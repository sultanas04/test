# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 17:50:00 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm
from shapely.geometry import box
import streamlit as st
import xarray as xr

# --- CONFIG HALAMAN ---
st.set_page_config(
    page_title="Dashboard Proyeksi Iklim Staklim Lampung",
    page_icon="⛈️",
    layout="wide",
)

st.title("⛈️ Dashboard Proyeksi Indeks Curah Hujan Ekstrem - Provinsi Lampung")
st.markdown(
    "Aplikasi interaktif analisis klimatologi bulanan dan musiman (SSP370 & SSP585) berbasis data CMIP6 BMKG."
)
st.write("---")

# =========================================================================
# 1. DATABASE FILE ID GOOGLE DRIVE
# =========================================================================
DRIVE_DATABASE = {
    "SSP370": {
        "Ensemble Mean": "1ZICcpa5WvzuERzCDRDouyPRVETPwPlSc",
        "Model 1 (CESM2-WACCM)": "1rxVRWJjShr-99Uk8qY7hk8VgpvhyvKy4",
        "Model 2 (GFDL-ESM4)": "1Wv8q2HPOEfsShh4AR5pTc0yk5JZA3gk5",
        "Model 3 (CMCC-CM2)": "1MRVQz0qUQAFPglffZVlXypHRragY4H3_",
        "Model 4 (INM-CM4-8)": "16evEEG2Ok7341Gu2-66-zz8Sksf96ZAU",
        "Model 5 (INM-CM5-0)": "1cmZbGeCHnmOa70-CcMfvI0yJ8KdRutvL",
        "Model 6 (NORESM2)": "1hY_yGXyUoPq7eTfXzCWeIKFASknNGWa9",
    },
    "SSP585": {
        "Ensemble Mean": "1xoXSowKqXB7j36SCmbVUSnoPX6EhXfrA",
        "Model 1 (CESM2-WACCM)": "1kH1jhHFZvuFZBb_vP_Trrtt2Ro3lPG-F",
        "Model 2 (GFDL-ESM4)": "1lcFwb3NDnuHlntAdt8-YERI0Ds9__qZJ",
        "Model 3 (CMCC-CM2)": "1I3Em2dhaVGuwRwh-NpPMWhSfpgrHhYmJ",
        "Model 4 (INM-CM4-8)": "1KJeUaaCAHfIFRSX321fCDvvR6HfE-Pz_",
        "Model 5 (INM-CM5-0)": "15wR9xgX6WmuGYv651oQfMuxyIUGpNEjC",
        "Model 6 (NORESM2)": "1SpzbI6uiwPiJbXj02xWStj765Ot81eXj",
    },
}

# =========================================================================
# 2. DEFINISI WARNA KUSTOM BMKG (DISKRET)
# =========================================================================
ch_colors = [
    (0.250980392156863, 0, 0),                       # 0 - 20   : ch1 (Cokelat Tua)
    (0.490196078431373, 0.0823529411764706, 0),      # 20 - 50  : ch2
    (1, 0.415686274509804, 0),                       # 50 - 100 : ch3 (Jingga)
    (1, 0.835294117647059, 0),                       # 100 - 150: ch4
    (1, 1, 0),                                       # 150 - 200: ch5 (Kuning)
    (0.666666666666667, 1, 0),                       # 200 - 300: ch6
    (0.501960784313725, 0.749019607843137, 0),       # 300 - 400: ch7
    (0.2, 0.6, 0),                                   # 400 - 500: ch8 (Hijau Daun)
]
cmap_kustom = ListedColormap(ch_colors)
clevels = [0, 20, 50, 100, 150, 200, 300, 400, 500]
norm_kustom = BoundaryNorm(clevels, cmap_kustom.N)

# =========================================================================
# 3. LOAD DATA GEOJSON & PEMBUATAN TOPENG INVERTED MASK
# =========================================================================
@st.cache_data
def load_geojson_and_mask():
    geojson_path = "lampung-2014.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        gdf = gdf.to_crs(epsg=4326)
        
        # LOGIKA CETAKAN TOPENG: Buat kotak raksasa lalu lubangi tengahnya dengan SHP Lampung
        lampung_union = gdf.unary_union
        giant_box = box(90, -15, 120, 0) # Kotak melingkupi seluruh area pandang
        inverted_geometry = giant_box.difference(lampung_union)
        gdf_inverted = gpd.GeoSeries([inverted_geometry], crs="EPSG:4326")
        
        return gdf, gdf_inverted
    return None, None

gdf_lampung, gdf_topeng_putih = load_geojson_and_mask()

# --- SIDEBAR FILTERS ---
st.sidebar.header("⚙️ Filter Analisis")
skenario = st.sidebar.selectbox("1. Pilih Skenario:", options=["SSP370", "SSP585"])

model_options = [
    "Ensemble Mean", "Model 1 (CESM2-WACCM)", "Model 2 (GFDL-ESM4)", 
    "Model 3 (CMCC-CM2)", "Model 4 (INM-CM4-8)", "Model 5 (INM-CM5-0)", "Model 6 (NORESM2)"
]
model_pilihan = st.sidebar.selectbox("2. Pilih Model:", options=model_options)

dict_var = {"pr": "Total Curah Hujan (mm/bulan)"}
var_pilihan = "pr"

# --- FUNGSI DOWNLOAD DATA ---
@st.cache_data
def get_data_from_drive(skenario_name, model_name):
    try: file_id = DRIVE_DATABASE[skenario_name][model_name]
    except KeyError: return None
    url = f"https://drive.google.com/uc?id={file_id}"
    clean_model_name = model_name.replace(" ", "_").replace("(", "").replace(")", "")
    local_filename = f"data_{skenario_name}_{clean_model_name}.nc"
    if not os.path.exists(local_filename):
        with st.spinner(f"Mengunduh data {model_name}..."):
            gdown.download(url, local_filename, quiet=True)
    return xr.open_dataset(local_filename)

ds = get_data_from_drive(skenario, model_pilihan)

if ds is None:
    st.warning("⚠️ File ID Google Drive belum dikonfigurasi lengkap.")
else:
    years = sorted(list(set(ds.time.dt.year.values)))
    st.sidebar.subheader("3. Rentang Tahun Analisis")
    tahun_mulai, tahun_selesai = st.sidebar.select_slider("Gabungkan Periode Tahun:", options=years, value=(2025, 2050))

    # Penyelarasan nama dimensi koordinat standar
    if "latitude" in ds.coords: ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords: ds = ds.rename({"longitude": "lon"})

    # Penyelarasan format bujur global (0-360 ke -180 s/d 180 jika diperlukan)
    if ds.lon.max() > 180:
        ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))
        ds = ds.sortby("lon")

    # Ambil data batas box Lampung diperluas sedikit agar interpolasi pantai mulus
    lat_start, lat_end = -6.2, -3.3
    if ds.lat.values[0] > ds.lat.values[-1]:
        lat_slice_fixed = slice(lat_end, lat_start)
    else:
        lat_slice_fixed = slice(lat_start, lat_end)

    ds_area = ds.sel(lat=lat_slice_fixed, lon=slice(103.3, 106.2), time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"))

    tab_bulanan, tab_musiman = st.tabs(["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"])

    # =========================================================================
    # TAB 1: VISUALISASI 12 BULAN (CANVAS CANVAS MASKING)
    # =========================================================================
    with tab_bulanan:
        st.subheader(f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}")
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        fig, axes = plt.subplots(3, 4, figsize=(15, 12), sharex=True, sharey=True)
        month_names = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

        for i, ax in enumerate(axes.flat):
            data_month = climatology_monthly.sel(month=i + 1)

            # 1. Gambar Kontur Iklim Seluruh Petak Kotak (Termasuk Laut)
            p = ax.contourf(
                data_month.lon, data_month.lat, data_month.values,
                levels=clevels, cmap=cmap_kustom, norm=norm_kustom, extend="max"
            )

            # 2. TIMPA DENGAN TOPENG PUTIH: Otomatis memutihkan area di luar SHP Lampung secara instan!
            if gdf_topeng_putih is not None:
                gdf_topeng_putih.plot(ax=ax, color='white', edgecolor='none', zorder=2)

            # 3. Gambar garis batas kabupaten Lampung di atas topeng putih
            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, alpha=1.0, zorder=3)

            ax.set_title(month_names[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4, zorder=1)
            
            # Kunci batas area koordinat layar peta agar presisi
            ax.set_xlim(103.5, 106.0)
            ax.set_ylim(-6.0, -3.5)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig.subplots_adjust(bottom=0.18, hspace=0.3, wspace=0.2)
        cbar_ax = fig.add_axes([0.15, 0.08, 0.7, 0.02])
        fig.colorbar(p, cax=cbar_ax, orientation="horizontal", label="mm/bulan")
        st.pyplot(fig)

    # =========================================================================
    # TAB 2: VISUALISASI MUSIMAN (CANVAS CANVAS MASKING)
    # =========================================================================
    with tab_musiman:
        st.subheader(f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}")
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {
            "DJF": "MUSIM BARAT / HUJAN (DJF)", "MAM": "MUSIM PERALIHAN I (MAM)", 
            "JJA": "MUSIM TIMUR / KEMARAU (JJA)", "SON": "MUSIM PERALIHAN II (SON)"
        }

        fig2, axes2 = plt.subplots(2, 2, figsize=(11, 10), sharex=True, sharey=True)

        for i, ax in enumerate(axes2.flat):
            sea = seasons_order[i]
            data_season = climatology_seasonal.sel(season=sea)

            # 1. Gambar Kontur Musiman
            p2 = ax.contourf(
                data_season.lon, data_season.lat, data_season.values,
                levels=clevels, cmap=cmap_kustom, norm=norm_kustom, extend="max"
            )

            # 2. Timpa dengan topeng putih
            if gdf_topeng_putih is not None:
                gdf_topeng_putih.plot(ax=ax, color='white', edgecolor='none', zorder=2)

            # 3. Gambar garis batas kabupaten
            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, alpha=1.0, zorder=3)

            ax.set_title(season_titles[sea], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4, zorder=1)
            
            ax.set_xlim(103.5, 106.0)
            ax.set_ylim(-6.0, -3.5)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig2.subplots_adjust(bottom=0.15, hspace=0.2, wspace=0.2)
        cbar_ax2 = fig2.add_axes([0.15, 0.06, 0.7, 0.02])
        fig2.colorbar(p2, cax=cbar_ax2, orientation="horizontal", label="mm/bulan")
        st.pyplot(fig2)

    ds.close()
