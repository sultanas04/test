# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 16:45:00 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rioxarray  # Diperlukan untuk melakukan masking/clipping data berdasarkan SHP
from matplotlib.colors import LinearSegmentedColormap
from shapely.geometry import mapping
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
    "Aplikasi interaktif analisis klimatologi bulanan dan musiman (SSP370 & SSP585) dengan Masking Wilayah SHP."
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
# 2. DEFINISI BATAS AREA KOORDINAT (Bbox)
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
# 3. DEFINISI GRADASI WARNA KUSTOM (Tuple RGB ch1 sampai ch8)
# =========================================================================
ch_colors = [
    (0.250980392156863, 0, 0),                       # ch1: Merah Tua / Cokelat
    (0.490196078431373, 0.0823529411764706, 0),      # ch2
    (1, 0.415686274509804, 0),                       # ch3: Jingga
    (1, 0.835294117647059, 0),                       # ch4
    (1, 1, 0),                                       # ch5: Kuning
    (0.666666666666667, 1, 0),                       # ch6
    (0.501960784313725, 0.749019607843137, 0),       # ch7
    (0.2, 0.6, 0),                                   # ch8: Hijau
]
cmap_kustom = LinearSegmentedColormap.from_list("Klimatologi_Lampung", ch_colors, N=256)

# =========================================================================
# 4. FUNGSI LOAD GEOJSON BATAS KABUPATEN
# =========================================================================
@st.cache_data
def load_geojson():
    geojson_path = "lampung-2014.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        # Menyamakan format CRS GeoPandas agar dikenali rioxarray
        if gdf.crs is None or gdf.crs != "EPSG:4326":
            gdf.set_crs(epsg=4326, inplace=True, allow_override=True)
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

    # --- PROSES MEMOTONG AREA BERDASARKAN BOUNDING BOX ---
    geo_box = REGIONS_LAMPUNG[wilayah_pilihan]
    ds_area = ds.sel(lat=geo_box["lat_slice"], lon=geo_box["lon_slice"], time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"))

    # --- PROSES INDEKS SPASIAL / MASKING UTK SHP (RIOXARRAY CLIPPING) ---
    # Langkah penting agar data NetCDF mengenali koordinat spasialnya untuk di-masking
    if "rio" not in ds_area.dims:
        ds_area = ds_area.rio.write_crs("EPSG:4326")
        if 'lon' in ds_area.coords and 'lat' in ds_area.coords:
            ds_area = ds_area.rio.set_spatial_dims(x='lon', y='lat')

    # Memotong data iklim secara presisi mengikuti lekukan bentuk SHP Lampung
    if gdf_lampung is not None and wilayah_pilihan == "Seluruh Provinsi Lampung":
        try:
            ds_area = ds_area.rio.clip(gdf_lampung.geometry.apply(mapping), gdf_lampung.crs, drop=False, invert=False)
        except Exception as e:
            pass

    tab_bulanan, tab_musiman = st.tabs(["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"])

    # =========================================================================
    # TAB 1: VISUALISASI 12 BULAN (DENGAN MASKING SHP DARATAN)
    # =========================================================================
    with tab_bulanan:
        st.subheader(f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}")
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        fig, axes = plt.subplots(3, 4, figsize=(15, 12), sharex=True, sharey=True)
        month_names = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

        if var_pilihan == "pr":
            clevels = [0, 20, 50, 100, 150, 200, 300, 400, 500]
        else:
            v_min = float(climatology_monthly.min().dropna(dim='month', how='all'))
            v_max = float(climatology_monthly.max().dropna(dim='month', how='all'))
            clevels = np.linspace(v_min, v_max, 9)

        for i, ax in enumerate(axes.flat):
            data_month = climatology_monthly.sel(month=i + 1)

            # Gambar kontur terisi (hanya di area daratan karena luar SHP bernilai NaN/Kosong)
            p = ax.contourf(
                data_month.lon, data_month.lat, data_month.values,
                levels=clevels, cmap=cmap_kustom,
                extend="max" if var_pilihan == "pr" else "neither"
            )

            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, alpha=0.9)

            ax.set_title(month_names[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_yticks([-6, -5.5, -5, -4.5, -4])
            ax.set_yticklabels(["6°S", "5.5°S", "5°S", "4.5°S", "4°S"])
            ax.set_xticks([104, 105, 106])
            ax.set_xticklabels(["104°E", "105°E", "106°E"])

        fig.subplots_adjust(bottom=0.18, hspace=0.3, wspace=0.2)
        cbar_ax = fig.add_axes([0.15, 0.08, 0.7, 0.02])
        fig.colorbar(p, cax=cbar_ax, orientation="horizontal", label=f"{ds[var_pilihan].attrs.get('units', 'mm/bulan')}")
        st.pyplot(fig)

    # =========================================================================
    # TAB 2: VISUALISASI MUSIMAN (DENGAN MASKING SHP DARATAN)
    # =========================================================================
    with tab_musiman:
        st.subheader(f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}")
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {"DJF": "MUSIM BARAT / HUJAN (DJF)", "MAM": "MUSIM PERALIHAN I (MAM)", "JJA": "MUSIM TIMUR / KEMARAU (JJA)", "SON": "MUSIM PERALIHAN II (SON)"}

        if var_pilihan == "pr":
            clevels_s = [0, 20, 50, 100, 150, 200, 300, 400, 500]
        else:
            clevels_s = np.linspace(float(climatology_seasonal.min()), float(climatology_seasonal.max()), 9)

        fig2, axes2 = plt.subplots(2, 2, figsize=(11, 10), sharex=True, sharey=True)

        for i, ax in enumerate(axes2.flat):
            sea = seasons_order[i]
            data_season = climatology_seasonal.sel(season=sea)

            p2 = ax.contourf(
                data_season.lon, data_season.lat, data_season.values,
                levels=clevels_s, cmap=cmap_kustom,
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
