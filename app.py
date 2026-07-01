# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 17:45:00 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import regionmask
from matplotlib.colors import ListedColormap, BoundaryNorm
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
    "Aplikasi interaktif analisis klimatologi bulanan dan musiman (SSP370 & SSP585) - Penyelarasan Koordinat & Masking 100% Bersih."
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

# Bounding box koordinat diperluas sedikit agar interpolasi contourf di pinggir pantai tidak terpotong cacat
REGIONS_LAMPUNG = {
    "Seluruh Provinsi Lampung": {"lat_slice": slice(-6.2, -3.3), "lon_slice": slice(103.3, 106.2)},
}

# =========================================================================
# 3. DEFINISI WARNA KUSTOM BMKG (DISKRET)
# =========================================================================
ch_colors = [
    (0.250980392156863, 0, 0),                       # 0 - 20   : ch1
    (0.490196078431373, 0.0823529411764706, 0),      # 20 - 50  : ch2
    (1, 0.415686274509804, 0),                       # 50 - 100 : ch3
    (1, 0.835294117647059, 0),                       # 100 - 150: ch4
    (1, 1, 0),                                       # 150 - 200: ch5
    (0.666666666666667, 1, 0),                       # 200 - 300: ch6
    (0.501960784313725, 0.749019607843137, 0),       # 300 - 400: ch7
    (0.2, 0.6, 0),                                   # 400 - 500: ch8
]
cmap_kustom = ListedColormap(ch_colors)
clevels = [0, 20, 50, 100, 150, 200, 300, 400, 500]
norm_kustom = BoundaryNorm(clevels, cmap_kustom.N)

@st.cache_data
def load_geojson():
    geojson_path = "lampung-2014.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        gdf = gdf.to_crs(epsg=4326)
        return gdf
    return None

gdf_lampung = load_geojson()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Filter Analisis")
skenario = st.sidebar.selectbox("1. Pilih Skenario:", options=["SSP370", "SSP585"])
model_options = ["Ensemble Mean", "Model 1 (CESM2-WACCM)", "Model 2 (GFDL-ESM4)", "Model 3 (CMCC-CM2)", "Model 4 (INM-CM4-8)", "Model 5 (INM-CM5-0)", "Model 6 (NORESM2)"]
model_pilihan = st.sidebar.selectbox("2. Pilih Model:", options=model_options)

dict_var = {"pr": "Total Curah Hujan (mm/bulan)"}
var_pilihan = "pr"

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

    # --- KUNCI PERBAIKAN 1: PENYELARASAN NAMA & FORMAT KOORDINAT GLOBAL ---
    if "latitude" in ds.coords: ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords: ds = ds.rename({"longitude": "lon"})

    # Paksa konversi jika bujur NetCDF bertipe 0-360 derajat ke standar -180 s/d 180
    if (ds.lon.max() > 180):
        ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))
        ds = ds.sortby("lon")

    # Ambil batas box Lampung
    geo_box = REGIONS_LAMPUNG["Seluruh Provinsi Lampung"]
    
    # Deteksi arah urutan Latitude (Ascending vs Descending)
    if ds.lat.values[0] > ds.lat.values[-1]:
        lat_slice_fixed = slice(geo_box["lat_slice"].stop, geo_box["lat_slice"].start)
    else:
        lat_slice_fixed = slice(geo_box["lat_slice"].start, geo_box["lat_slice"].stop)

    # Potong data awal
    ds_area = ds.sel(lat=lat_slice_fixed, lon=geo_box["lon_slice"], time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"))

    # =========================================================================
    # KUNCI PERBAIKAN 2: INTEGRASI MASK_3D DENGAN PROTEKSI MULTI-POLIGON
    # =========================================================================
    if gdf_lampung is not None:
        try:
            # Mengunci nama koordinat netCDF agar sinkron total dengan struktur GeoJSON
            lampung_rm = regionmask.from_geopandas(gdf_lampung)
            mask_3d = lampung_rm.mask_3D(ds_area.lon, ds_area.lat, lon_name="lon", lat_name="lat")
            mask_final = mask_3d.any(dim="region")
            
            # Eksekusi pemotongan mutlak. Semua di luar arsir poligon DIPAKSA menjadi NaN (Putih Bersih)
            ds_area = ds_area.where(mask_final)
        except Exception as e:
            print(f"[LOG MASK_3D ERROR] {e}")

    tab_bulanan, tab_musiman = st.tabs(["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"])

    # =========================================================================
    # TAB 1: VISUALISASI 12 BULAN
    # =========================================================================
    with tab_bulanan:
        st.subheader(f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}")
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        fig, axes = plt.subplots(3, 4, figsize=(15, 12), sharex=True, sharey=True)
        month_names = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

        for i, ax in enumerate(axes.flat):
            data_month = climatology_monthly.sel(month=i + 1)

            # Plotting kontur diskret
            p = ax.contourf(
                data_month.lon, data_month.lat, data_month.values,
                levels=clevels, 
                cmap=cmap_kustom,
                norm=norm_kustom,
                extend="max"
            )

            # Gambar ulang garis tepi SHP di atas kontur
            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.7, alpha=1.0)

            ax.set_title(month_names[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_xlim(103.4, 106.1)
            ax.set_ylim(-6.1, -3.4)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig.subplots_adjust(bottom=0.18, hspace=0.3, wspace=0.2)
        cbar_ax = fig.add_axes([0.15, 0.08, 0.7, 0.02])
        fig.colorbar(p, cax=cbar_ax, orientation="horizontal", label="mm/bulan")
        st.pyplot(fig)

    # =========================================================================
    # TAB 2: VISUALISASI MUSIMAN
    # =========================================================================
    with tab_musiman:
        st.subheader(f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}")
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {"DJF": "MUSIM BARAT / HUJAN (DJF)", "MAM": "MUSIM PERALIHAN I (MAM)", "JJA": "MUSIM TIMUR / KEMARAU (JJA)", "SON": "MUSIM PERALIHAN II (SON)"}

        fig2, axes2 = plt.subplots(2, 2, figsize=(11, 10), sharex=True, sharey=True)

        for i, ax in enumerate(axes2.flat):
            sea = seasons_order[i]
            data_season = climatology_seasonal.sel(season=sea)

            p2 = ax.contourf(
                data_season.lon, data_season.lat, data_season.values,
                levels=clevels, 
                cmap=cmap_kustom,
                norm=norm_kustom,
                extend="max"
            )

            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.7, alpha=1.0)

            ax.set_title(season_titles[sea], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_xlim(103.4, 106.1)
            ax.set_ylim(-6.1, -3.4)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig2.subplots_adjust(bottom=0.15, hspace=0.2, wspace=0.2)
        cbar_ax2 = fig2.add_axes([0.15, 0.06, 0.7, 0.02])
        fig2.colorbar(p2, cax=cbar_ax2, orientation="horizontal", label="mm/bulan")
        st.pyplot(fig2)

    ds.close()
