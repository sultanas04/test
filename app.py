# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 15:45:00 2026

@author: BMKG Staklim Lampung
"""

import os
import gdown
import matplotlib.pyplot as plt
import streamlit as st
import xarray as xr

# --- CONFIG HALAMAN ---
st.set_page_config(
    page_title="Dashboard Klimatologi Proyeksi Lampung",
    page_icon="⛈️",
    layout="wide",
)

st.title("⛈️ Dashboard Analisis Klimatologi & Musiman Proyeksi Curah Hujan")
st.markdown(
    "Analisis rata-rata spasial bulanan dan musiman pada periode rentang tahun proyeksi yang dipilih (Data CMIP6)."
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
# 2. DEFINISI BATAS KOORDINAT KABUPATEN DI LAMPUNG
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

skenario = st.sidebar.selectbox("1. Pilih Skenario:", options=["SSP370", "SSP585"])

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

wilayah_pilihan = st.sidebar.selectbox(
    "3. Fokus Wilayah:", options=list(REGIONS_LAMPUNG.keys())
)

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
    clean_model_name = (
        model_name.replace(" ", "_").replace("(", "").replace(")", "")
    )
    local_filename = f"data_{skenario_name}_{clean_model_name}.nc"

    if not os.path.exists(local_filename):
        with st.spinner(f"Mengunduh data {model_name} dari GDrive..."):
            gdown.download(url, local_filename, quiet=True)

    return xr.open_dataset(local_filename)


# --- EKSEKUSI PEMBACAAN DATA ---
ds = get_data_from_drive(skenario, model_pilihan)

if ds is None:
    st.warning("⚠️ File ID Google Drive belum dikonfigurasi dengan benar.")
else:
    # --- RENTANG WAKTU SLIDER TAHUN ---
    years = sorted(list(set(ds.time.dt.year.values)))
    st.sidebar.subheader("5. Tentukan Rentang Tahun Analisis")
    tahun_mulai, tahun_selesai = st.sidebar.select_slider(
        "Gabungkan Rentang Tahun:", options=years, value=(2021, 2030)
    )

    # --- FILTER SPASIAL DAN WAKTU AWAL ---
    geo_box = REGIONS_LAMPUNG[wilayah_pilihan]
    ds_area = ds.sel(
        lat=geo_box["lat_slice"],
        lon=geo_box["lon_slice"],
        time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"),
    )

    # --- PROSES METODE INTERPOLASI (SMOOTHING PETA) ---
    st.sidebar.subheader("🎨 Desain Visual")
    smooth_option = st.sidebar.checkbox(
        "Aktifkan Smoothing Peta (Interpolasi)", value=True
    )
    shading_method = "gouraud" if smooth_option else "flat"

    # --- TAMPILAN UTAMA BERBASIS TAB ---
    tab_bulanan, tab_musiman = st.tabs(
        ["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"]
    )

    # ==========================================
    # TAB 1: VISUALISASI 12 BULAN (KLIMATOLOGI)
    # ==========================================
    with tab_bulanan:
        st.subheader(
            f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}"
        )
        st.caption(
            f"Data menunjukkan nilai rata-rata tiap bulan sepanjang tahun yang dipilih untuk variabel {dict_var[var_pilihan]}."
        )

        # Proses perhitungan rata-rata klimatologi bulanan (Groupby)
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        # Membuat Grid Plot 3x4 untuk 12 Bulan
        fig, axes = plt.subplots(3, 4, figsize=(15, 12), sharex=True, sharey=True)
        month_names = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]

        # Cari nilai min dan max area agar gradasi warna konsisten di semua bulan
        vmin = float(climatology_monthly.min())
        vmax = float(climatology_monthly.max())
        cmap_color = "YlGnBu" if var_pilihan != "pr" else "Blues"

        for i, ax in enumerate(axes.flat):
            # i+1 merepresentasikan angka bulan (1=Jan, 12=Des)
            data_month = climatology_monthly.sel(month=i + 1)

            # Implementasi shading='gouraud' membuat peta kotak piksel kasar berubah menjadi halus/smooth
            p = ax.pcolormesh(
                data_month.lon,
                data_month.lat,
                data_month.values,
                shading=shading_method,
                cmap=cmap_color,
                vmin=vmin,
                vmax=vmax,
            )
            ax.set_title(month_names[i], fontsize=12, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.3)

        # Tambahkan satu Colorbar besar terpusat di bagian kanan
        fig.subplots_adjust(right=0.88, hspace=0.3, wspace=0.15)
        cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.7])
        fig.colorbar(p, cax=cbar_ax, label=ds[var_pilihan].attrs.get("units", ""))

        st.pyplot(fig)

    # ==========================================
    # TAB 2: VISUALISASI MUSIMAN (SEASONAL)
    # ==========================================
    with tab_musiman:
        st.subheader(
            f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}"
        )
        st.caption(
            "Pembagian musim standard meteorologi: DJF (Des-Jan-Feb/Barat), MAM (Mar-Apr-Mei/Peralihan 1), JJA (Jun-Jul-Agt/Timur), SON (Sep-Okt-Nov/Peralihan 2)."
        )

        # Proses perhitungan rata-rata berdasarkan musim (Groupby 'time.season')
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        # Susun urutan musim agar logis secara meteorologi Indonesia
        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {
            "DJF": "Musim Barat / Hujan (DJF)",
            "MAM": "Musim Peralihan I (MAM)",
            "JJA": "Musim Timur / Kemarau (JJA)",
            "SON": "Musim Peralihan II (SON)",
        }

        col_left, col_right = st.columns([3, 1])

        with col_left:
            fig2, axes2 = plt.subplots(2, 2, figsize=(12, 10), sharex=True, sharey=True)
            vmin_s = float(climatology_seasonal.min())
            vmax_s = float(climatology_seasonal.max())

            for i, ax in enumerate(axes2.flat):
                sea = seasons_order[i]
                data_season = climatology_seasonal.sel(season=sea)

                p2 = ax.pcolormesh(
                    data_season.lon,
                    data_season.lat,
                    data_season.values,
                    shading=shading_method,
                    cmap=cmap_color,
                    vmin=vmin_s,
                    vmax=vmax_s,
                )
                ax.set_title(season_titles[sea], fontsize=12, fontweight="bold")
                ax.grid(True, linestyle="--", alpha=0.3)

            fig2.subplots_adjust(right=0.88, hspace=0.2, wspace=0.15)
            cbar_ax2 = fig2.add_axes([0.92, 0.15, 0.02, 0.7])
            fig2.colorbar(p2, cax=cbar_ax2, label=ds[var_pilihan].attrs.get("units", ""))

            st.pyplot(fig2)

        with col_right:
            st.markdown("#### 📝 Insight Singkat")
            st.info(
                f"Analisis komparasi spasial antar musim mempermudah dalam melihat pergeseran puncak musim hujan atau tingkat keparahan musim kemarau di wilayah **{wilayah_pilihan}** pada masa depan."
            )

    ds.close()
