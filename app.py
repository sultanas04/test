# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 17:00:00 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rioxarray  # Ekstensi penting untuk memotong (clipping) data netCDF
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
    "Aplikasi interaktif analisis klimatologi bulanan dan musiman (SSP370 & SSP585) dengan Masking Wilayah SHP & Warna Kustom Terkunci."
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
# 2. DEFINISI BATAS AREA KOORDINAT (Bbox Approximation)
# =========================================================================
REGIONS_LAMPUNG = {
    "Seluruh Provinsi Lampung": {"lat_slice": slice(-6.0, -3.5), "lon_slice": slice(103.5, 106.0)},
    "Bandar Lampung": {"lat_slice": slice(-5.5, -5.3), "lon_slice": slice(105.2, 105.4)},
    "Lampung Selatan": {"lat_slice": slice(-6.0, -5.3), "lon_slice": slice(105.0, 106.0)},
    "Lampung Tengah": {"lat_slice": slice(-5.2, -4.5), "lon_slice": slice(104.7, 105.8)},
    "Lampung Utara": {"lat_slice": slice(-5.0, -4.3), "lon_slice": slice(104.5, 105.2)},
    "Metro": {"lat_slice": slice(-5.1, -4.9), "lon_slice": slice(105.2, 105.4)},
}

# =========================================================================
# 3. DEFINISI WARNA KUSTOM (DIKUNCI OLEH BOUNDARYNORM AGAR WARNA SESUAI NILAI)
# =========================================================================
ch_colors = [
    (0.250980392156863, 0, 0),                       # 0 - 20   : ch1 (Merah Tua/Cokelat)
    (0.490196078431373, 0.0823529411764706, 0),      # 20 - 50  : ch2
    (1, 0.415686274509804, 0),                       # 50 - 100 : ch3 (Jingga)
    (1, 0.835294117647059, 0),                       # 100 - 150: ch4
    (1, 1, 0),                                       # 150 - 200: ch5 (Kuning)
    (0.666666666666667, 1, 0),                       # 200 - 300: ch6
    (0.501960784313725, 0.749019607843137, 0),       # 300 - 400: ch7
    (0.2, 0.6, 0),                                   # 400 - 500: ch8 (Hijau Tua)
]
cmap_kustom = ListedColormap(ch_colors)

# Batas kelas curah hujan bulanan BMKG sesuai gambar contoh Anda
clevels = [0, 20, 50, 100, 150, 200, 300, 400, 500]
norm_kustom = BoundaryNorm(clevels, cmap_kustom.N)

# =========================================================================
# 4. FUNGSI LOAD GEOJSON BATAS KABUPATEN
# =========================================================================
@st.cache_data
def load_geojson():
    geojson_path = "lampung-2014.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        # Amankan proyeksi koordinat ke standar geografis WGS84
        gdf = gdf.to_crs(epsg=4326)
        return gdf
    return None

gdf_lampung = load_geojson()

# --- SIDEBAR FILTERS ---
st.sidebar.header("⚙️ Filter Analisis")
skenario = st.sidebar.selectbox("1. Pilih Skenario:", options=["SSP370", "SSP585"])

model_options = ["Ensemble Mean", "Model 1 (CESM2-WACCM)", "Model 2 (GFDL-ESM4)", "Model 3 (CMCC-CM2)", "Model 4 (INM-CM4-8)", "Model 5 (INM-CM5-0)", "Model 6 (NORESM2)"]
model_pilihan = st.sidebar.selectbox("2. Pilih Model:", options=model_options)
wilayah_pilihan = st.sidebar.selectbox("3. Fokus Wilayah:", options=list(REGIONS_LAMPUNG.keys()))

dict_var = {
    "pr": "Total Curah Hujan (mm/bulan)",
    "hh": "Jumlah Hari Hujan (>=1mm)",
    "R10mm": "Jumlah Hari Hujan >10mm",
    "R20mm": "Jumlah Hari Hujan >20mm",
    "R50mm": "Jumlah Hari Hujan >50mm",
    "R100mm": "Jumlah Hari Hujan >100mm",
}
var_pilihan = st.sidebar.selectbox("4. Pilih Indeks Iklim:", options=list(dict_var.keys()), format_func=lambda x: dict_var[x])

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
    st.sidebar.subheader("5. Rentang Tahun Analisis")
    tahun_mulai, tahun_selesai = st.sidebar.select_slider("Gabungkan Periode Tahun:", options=years, value=(2025, 2050))

    # --- PENYERAGAMAN KOORDINAT NAMA DIMENSI ---
    if "latitude" in ds.coords: ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords: ds = ds.rename({"longitude": "lon"})

    # Potong data waktu dan kotak wilayah dasar (bounding box)
    geo_box = REGIONS_LAMPUNG[wilayah_pilihan]

    # Mengantisipasi jika urutan koordinat lintang (lat) terbalik arah pada model tertentu
    lat_start, lat_end = geo_box["lat_slice"].start, geo_box["lat_slice"].stop
    if ds.lat.values[0] > ds.lat.values[-1]:
        lat_slice_fixed = slice(lat_end, lat_start)
    else:
        lat_slice_fixed = slice(lat_start, lat_end)

    ds_area = ds.sel(lat=lat_slice_fixed, lon=geo_box["lon_slice"], time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"))

    # --- PROSES MASKING/CLIPPING DATA BERDASARKAN POLIGON SHP ---
    ds_area = ds_area.rio.write_crs("EPSG:4326")
    if gdf_lampung is not None and wilayah_pilihan == "Seluruh Provinsi Lampung":
        try:
            # Memotong netCDF presisi mengikuti lekukan batas daratan GeoJSON Lampung
            ds_area = ds_area.rio.clip(gdf_lampung.geometry, gdf_lampung.crs, drop=False)
        except Exception as e:
            print(f"[LOG ERROR MASKING] {e}")

    tab_bulanan, tab_musiman = st.tabs(["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"])

    # =========================================================================
    # TAB 1: VISUALISASI 12 BULAN (TERKUNCI MASKING & KELAS WARNA)
    # =========================================================================
    with tab_bulanan:
        st.subheader(f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}")
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        fig, axes = plt.subplots(3, 4, figsize=(15, 12), sharex=True, sharey=True)
        month_names = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

        # Penyesuaian skala jika user memilih indeks di luar pr (Curah Hujan Bulanan)
        if var_pilihan == "pr":
            active_levels = clevels
            active_norm = norm_kustom
        else:
            v_min = float(np.nanmin(climatology_monthly.values))
            v_max = float(np.nanmax(climatology_monthly.values))
            active_levels = np.linspace(v_min, v_max, 9)
            active_norm = BoundaryNorm(active_levels, cmap_kustom.N)

        for i, ax in enumerate(axes.flat):
            data_month = climatology_monthly.sel(month=i + 1)

            # Plot contourf terisi hanya pada area daratan yang lolos masking poligon
            p = ax.contourf(
                data_month.lon, data_month.lat, data_month.values,
                levels=active_levels, 
                cmap=cmap_kustom,
                norm=active_norm,
                extend="max" if var_pilihan == "pr" else "neither"
            )

            # Overlay garis batas administrasi kabupaten
            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, alpha=0.9)

            ax.set_title(month_names[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        # Menempatkan Colorbar Horizontal di Sisi Bawah Grid Sesuai Contoh Gambar
        fig.subplots_adjust(bottom=0.18, hspace=0.3, wspace=0.2)
        cbar_ax = fig.add_axes([0.15, 0.08, 0.7, 0.02])
        fig.colorbar(p, cax=cbar_ax, orientation="horizontal", label=f"{ds[var_pilihan].attrs.get('units', 'mm/bulan')}")
        st.pyplot(fig)

    # =========================================================================
    # TAB 2: VISUALISASI MUSIMAN (TERKUNCI MASKING & KELAS WARNA)
    # =========================================================================
    with tab_musiman:
        st.subheader(f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}")
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {"DJF": "MUSIM BARAT / HUJAN (DJF)", "MAM": "MUSIM PERALIHAN I (MAM)", "JJA": "MUSIM TIMUR / KEMARAU (JJA)", "SON": "MUSIM PERALIHAN II (SON)"}

        if var_pilihan == "pr":
            active_levels_s = clevels
            active_norm_s = norm_kustom
        else:
            active_levels_s = np.linspace(float(np.nanmin(climatology_seasonal.values)), float(np.nanmax(climatology_seasonal.values)), 9)
            active_norm_s = BoundaryNorm(active_levels_s, cmap_kustom.N)

        fig2, axes2 = plt.subplots(2, 2, figsize=(11, 10), sharex=True, sharey=True)

        for i, ax in enumerate(axes2.flat):
            sea = seasons_order[i]
            data_season = climatology_seasonal.sel(season=sea)

            p2 = ax.contourf(
                data_season.lon, data_season.lat, data_season.values,
                levels=active_levels_s, 
                cmap=cmap_kustom,
                norm=active_norm_s,
                extend="max" if var_pilihan == "pr" else "neither"
            )

            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, alpha=0.9)

            ax.set_title(season_titles[sea], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig2.subplots_adjust(bottom=0.15, hspace=0.2, wspace=0.2)
        cbar_ax2 = fig2.add_axes([0.15, 0.06, 0.7, 0.02])
        fig2.colorbar(p2, cax=cbar_ax2, orientation="horizontal", label=f"{ds[var_pilihan].attrs.get('units', 'mm/bulan')}")
        st.pyplot(fig2)

    ds.close()
