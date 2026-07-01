# -*- coding: utf-8 -*-
"""
Created on Tue Jun 30 14:20:41 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import matplotlib.pyplot as plt
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
    "Aplikasi interaktif analisis proyeksi iklim bulanan (SSP370 & SSP585) berbasis data CMIP6."
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
# 2. DEFINISI BATAS KOORDINAT KABUPATEN DI LAMPUNG (Bbox Approximation)
# =========================================================================
REGIONS_LAMPUNG = {
    "Seluruh Provinsi Lampung": {
        "lat_slice": slice(-6.0, -3.5),
        "lon_slice": slice(103.5, 106.0),
    },
    "Bandar Lampung": {
        "lat_slice": slice(-5.5, -5.3),
        "lon_slice": slice(105.2, 105.4),
    },
    "Lampung Selatan": {
        "lat_slice": slice(-6.0, -5.3),
        "lon_slice": slice(105.0, 106.0),
    },
    "Lampung Tengah": {
        "lat_slice": slice(-5.2, -4.5),
        "lon_slice": slice(104.7, 105.8),
    },
    "Lampung Utara": {
        "lat_slice": slice(-5.0, -4.3),
        "lon_slice": slice(104.5, 105.2),
    },
    "Metro": {"lat_slice": slice(-5.1, -4.9), "lon_slice": slice(105.2, 105.4)},
}

# --- SIDEBAR FILTERS ---
st.sidebar.header("⚙️ Filter Analisis")

# 1. Pilih Skenario
skenario = st.sidebar.selectbox("1. Pilih Skenario:", options=["SSP370", "SSP585"])

# 2. Pilih Model (NAMA SUDAH DISAMAKAN DENGAN DI ATAS DAN LENGKAP 6 MODEL)
model_options = [
    "Ensemble Mean",
    "Model 1 (CESM2-WACCM)",
    "Model 2 (GFDL-ESM4)",
    "Model 3 (CMCC-CM2)",
    "Model 4 (INM-CM4-8)",
    "Model 5 (INM-CM5-0)",
    "Model 6 (NORESM2)",
]
model_pilihan = st.sidebar.selectbox("2. Pilih Model:", options=model_options)

# 3. Pilih Wilayah (Provinsi / Kabupaten)
wilayah_pilihan = st.sidebar.selectbox(
    "3. Fokus Wilayah:", options=list(REGIONS_LAMPUNG.keys())
)

# 4. Pilih Indeks Variabel
dict_var = {
    "pr": "Total Curah Hujan (mm/bulan)",
    "hh": "Jumlah Hari Hujan (>=1mm)",
    "R10mm": "Jumlah Hari Hujan >10mm",
    "R20mm": "Jumlah Hari Hujan >20mm",
    "R50mm": "Jumlah Hari Hujan >50mm",
    "R100mm": "Jumlah Hari Hujan >100mm",
}
var_pilihan = st.sidebar.selectbox(
    "4. Pilih Indeks Iklim:",
    options=list(dict_var.keys()),
    format_func=lambda x: dict_var[x],
)


# --- FUNGSI DOWNLOAD DATA DARI GDRIVE ---
@st.cache_data
def get_data_from_drive(skenario_name, model_name):
    try:
        file_id = DRIVE_DATABASE[skenario_name][model_name]
    except KeyError:
        return None

    url = f"https://drive.google.com/uc?id={file_id}"

    # Mengganti karakter kurung dan spasi agar nama file lokal aman/bersih
    clean_model_name = (
        model_name.replace(" ", "_").replace("(", "").replace(")", "")
    )
    local_filename = f"data_{skenario_name}_{clean_model_name}.nc"

    if not os.path.exists(local_filename):
        with st.spinner(
            f"Mengunduh data {model_name} ({skenario_name}) dari Google Drive..."
        ):
            gdown.download(url, local_filename, quiet=True)

    return xr.open_dataset(local_filename)


# --- EKSEKUSI PEMBACAAN DATA ---
ds = get_data_from_drive(skenario, model_pilihan)

if ds is None:
    st.warning(
        "⚠️ File ID Google Drive belum dikonfigurasi lengkap di dalam skrip."
    )
else:
    # --- PILIH RENTANG WAKTU (TAHUN) ---
    years = sorted(list(set(ds.time.dt.year.values)))
    st.sidebar.subheader("5. Rentang Waktu")
    tahun_mulai, tahun_selesai = st.sidebar.select_slider(
        "Pilih Rentang Tahun:", options=years, value=(years[0], years[-1])
    )

    # --- FILTER DATA BERDASARKAN RENTANG WAKTU DAN SPASIAL (WILAYAH) ---
    ds_filtered = ds.sel(
        time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31")
    )

    geo_box = REGIONS_LAMPUNG[wilayah_pilihan]
    ds_filtered = ds_filtered.sel(
        lat=geo_box["lat_slice"], lon=geo_box["lon_slice"]
    )

    # --- INPUT USER UNTUK BULAN TAMPILAN PETA ---
    available_months = [str(t)[:7] for t in ds_filtered.time.values]
    selected_month = st.select_slider(
        "📅 Geser untuk memilih Bulan/Tahun Tampilan Peta:",