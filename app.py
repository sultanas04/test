# -*- coding: utf-8 -*-
"""
Created on Wed Jul 01 18:15:00 2026

@author: BMKG Staklim Lampung
"""

import io
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
    "Aplikasi interaktif analisis klimatologi bulanan dan musiman dengan Fitur Pelabelan Nama Kota/Kabupaten Otomatis."
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

# =========================================================================
# 3. LOAD DATA GEOJSON & PEMBUATAN TOPENG INVERTED MASK
# =========================================================================
@st.cache_data
def load_geojson_and_mask():
    geojson_path = "lampung-2014.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        gdf = gdf.to_crs(epsg=4326)
        
        # Cari nama kolom yang berisi info nama daerah (biasasanya 'KAB_KOT', 'NAME_2', atau 'nama')
        # Kita buat kolom standar baru bernama 'LABEL_NAMA' agar dinamis
        possible_cols = ['KAB_KOT', 'NAME_2', 'nama', 'NAMA_KABUP']
        col_found = None
        for col in possible_cols:
            if col in gdf.columns:
                col_found = col
                break
        
        if col_found:
            gdf['LABEL_NAMA'] = gdf[col_found].str.title()
        else:
            # Jika tidak ketemu, gunakan kolom string pertama yang tersedia
            str_cols = gdf.select_dtypes(include=['object']).columns
            if len(str_cols) > 0:
                gdf['LABEL_NAMA'] = gdf[str_cols[0]].str.title()
            else:
                gdf['LABEL_NAMA'] = ""

        lampung_union = gdf.unary_union
        giant_box = box(90, -15, 120, 0)
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

    if "latitude" in ds.coords: ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords: ds = ds.rename({"longitude": "lon"})

    if ds.lon.max() > 180:
        ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))
        ds = ds.sortby("lon")

    lat_start, lat_end = -6.2, -3.3
    if ds.lat.values[0] > ds.lat.values[-1]:
        lat_slice_fixed = slice(lat_end, lat_start)
    else:
        lat_slice_fixed = slice(lat_start, lat_end)

    ds_area = ds.sel(lat=lat_slice_fixed, lon=slice(103.3, 106.2), time=slice(f"{tahun_mulai}-01-01", f"{tahun_selesai}-12-31"))

    tab_bulanan, tab_musiman = st.tabs(["📅 Analisis 12 Bulan", "🍂 Analisis Musiman (Seasonal)"])

    # =========================================================================
    # TAB 1: VISUALISASI 12 BULAN (DENGAN LABEL NAMA DAERAH)
    # =========================================================================
    with tab_bulanan:
        st.subheader(f"📊 Klimatologi Rata-Rata Bulanan Periode {tahun_mulai} - {tahun_selesai}")
        climatology_monthly = ds_area[var_pilihan].groupby("time.month").mean(dim="time")

        fig, axes = plt.subplots(3, 4, figsize=(16, 13), sharex=True, sharey=True)
        month_names = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

        for i, ax in enumerate(axes.flat):
            data_month = climatology_monthly.sel(month=i + 1)

            p = ax.contourf(
                data_month.lon, data_month.lat, data_month.values,
                levels=clevels, cmap=cmap_kustom, norm=norm_kustom, extend="max"
            )

            if gdf_topeng_putih is not None:
                gdf_topeng_putih.plot(ax=ax, color='white', edgecolor='none', zorder=2)

            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.5, alpha=1.0, zorder=3)
                
                # --- KUNCI LOGIKA: PLOT NAMA KOTA/KABUPATEN ---
                for _, row in gdf_lampung.iterrows():
                    if row['LABEL_NAMA']:
                        # Dapatkan titik koordinat tengah (centroid) wilayah
                        centroid = row['geometry'].centroid
                        # Tulis teks nama daerah di atas peta
                        ax.text(
                            centroid.x, centroid.y, 
                            row['LABEL_NAMA'].replace("Kabupaten ", "").replace("Kota ", ""), # Singkat teks agar muat
                            fontsize=6, 
                            fontweight="bold",
                            color="black",
                            ha="center", 
                            va="center",
                            zorder=4,
                            # Memberikan efek outline putih tipis di belakang tulisan agar mudah terbaca
                            path_effects=[] 
                        )

            ax.set_title(month_names[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.3, zorder=1)
            
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

        img_buffer_monthly = io.BytesIO()
        fig.savefig(img_buffer_monthly, format='png', dpi=300, bbox_inches='tight')
        img_buffer_monthly.seek(0)

        st.download_button(
            label="💾 Download Peta Bulanan dengan Label (PNG)",
            data=img_buffer_monthly,
            file_name=f"Proyeksi_Bulanan_Label_{skenario}_{tahun_mulai}_{tahun_selesai}.png",
            mime="image/png"
        )

    # =========================================================================
    # TAB 2: VISUALISASI MUSIMAN (DENGAN LABEL NAMA DAERAH)
    # =========================================================================
    with tab_musiman:
        st.subheader(f"🍂 Analisis Rata-Rata Musiman Periode {tahun_mulai} - {tahun_selesai}")
        climatology_seasonal = ds_area[var_pilihan].groupby("time.season").mean(dim="time")

        seasons_order = ["DJF", "MAM", "JJA", "SON"]
        season_titles = {
            "DJF": "MUSIM BARAT / HUJAN (DJF)", "MAM": "MUSIM PERALIHAN I (MAM)", 
            "JJA": "MUSIM TIMUR / KEMARAU (JJA)", "SON": "MUSIM PERALIHAN II (SON)"
        }

        fig2, axes2 = plt.subplots(2, 2, figsize=(12, 11), sharex=True, sharey=True)

        for i, ax in enumerate(axes2.flat):
            sea = seasons_order[i]
            data_season = climatology_seasonal.sel(season=sea)

            p2 = ax.contourf(
                data_season.lon, data_season.lat, data_season.values,
                levels=clevels, cmap=cmap_kustom, norm=norm_kustom, extend="max"
            )

            if gdf_topeng_putih is not None:
                gdf_topeng_putih.plot(ax=ax, color='white', edgecolor='none', zorder=2)

            if gdf_lampung is not None:
                gdf_lampung.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.5, alpha=1.0, zorder=3)
                
                # --- PLOT NAMA KOTA/KABUPATEN DI TAB MUSIMAN ---
                for _, row in gdf_lampung.iterrows():
                    if row['LABEL_NAMA']:
                        centroid = row['geometry'].centroid
                        ax.text(
                            centroid.x, centroid.y, 
                            row['LABEL_NAMA'].replace("Kabupaten ", "").replace("Kota ", ""),
                            fontsize=7, # Ukuran teks sedikit lebih besar karena panelnya lebih luas (2x2)
                            fontweight="bold",
                            color="black",
                            ha="center", 
                            va="center",
                            zorder=4
                        )

            ax.set_title(season_titles[sea], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.3, zorder=1)
            
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

        img_buffer_seasonal = io.BytesIO()
        fig2.savefig(img_buffer_seasonal, format='png', dpi=300, bbox_inches='tight')
        img_buffer_seasonal.seek(0)

        st.download_button(
            label="💾 Download Peta Musiman dengan Label (PNG)",
            data=img_buffer_seasonal,
            file_name=f"Proyeksi_Musiman_Label_{skenario}_{tahun_mulai}_{tahun_selesai}.png",
            mime="image/png"
        )

    ds.close()
