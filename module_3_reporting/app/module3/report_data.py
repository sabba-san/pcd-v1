# report_data.py
from datetime import datetime


# ==================================================
# TRIBUNAL CASE INFORMATION
# (Static – since no login / no real filing)
# ==================================================

TRIBUNAL_CASE = {
    "tribunal": "Tribunal Tuntutan Pengguna Malaysia",
    "lokasi_tribunal": "Shah Alam",
    "no_tuntutan": "TTPM/SGR/2026/000123",
    "tarikh_jana": datetime.now().strftime("%d-%m-%Y"),
    "amaun_tuntutan": "RM 12,000.00",
    "dokumen": "Dokumen Sokongan Borang 1",
    "negeri": "Selangor"
}


# ==================================================
# PIHAK TERLIBAT (CLAIMANT & RESPONDENT DETAILS)
# ==================================================
# NOTE: Update these fields with actual claimant/respondent information
# These will appear in the BORANG 1 PDF export

PIHAK_YANG_MENUNTUT = {
    "nama": "Ahmad bin Abdullah",                    # Claimant's full name
    "no_kp": "880515-14-5678",                       # IC/Passport number
    "alamat_1": "No. 12, Jalan Harmoni 3/5",        # Address line 1
    "alamat_2": "Taman Harmoni, 43000 Kajang",      # Address line 2 (city, postcode)
    "no_telefon": "012-345 6789",                   # Phone number
    "email": "ahmad.abdullah@email.com",            # Email address
    "keterangan": "Pemilik unit kediaman"           # Description
}

PENENTANG = {
    "nama": "ABC Development Sdn. Bhd.",            # Respondent/Developer name
    "no_pendaftaran": "201901234567 (123456-A)",    # Company registration number
    "alamat_1": "Level 10, Menara ABC",             # Address line 1
    "alamat_2": "Jalan Sultan Ismail, 50250 KL",   # Address line 2
    "no_telefon": "03-2123 4567",                   # Phone number
    "email": "info@abcdevelopment.com.my",          # Email/Fax
    "keterangan": "Pemaju projek perumahan"         # Description
}


# ==================================================
# BUILD SUMMARY STATISTICS (FROM DASHBOARD STATS)
# ==================================================

def build_summary_stats(stats):
    return {
        "jumlah_kecacatan": stats.get("total", 0),
        "belum_diselesaikan": stats.get("pending", 0),
        "telah_diselesaikan": stats.get("completed", 0),
        "kritikal": stats.get("critical", 0)
    }


# ==================================================
# BUILD DEFECT DETAILS (TABLE → REPORT)
# ==================================================

def build_defect_list(defects, role):
    """
    Uses ONLY fields already available in dummy_data.py
    Builds defect list for report.
    Remarks (ulasan) are ONLY included for Homeowner.
    """
    report_defects = []

    for d in defects:
        # 1️⃣ Create defect item FIRST
        defect_item = {
            "id_kecacatan": d["id"],
            "unit": d["unit"],
            "keterangan": d["desc"],
            "status": d["status"],
            "tarikh_akhir": d.get("deadline", "-"),
            "tertunggak": "Ya" if d.get("is_overdue") else "Tidak",
            "patuh_hda": "Ya" if d.get("hda_compliant") else "Tidak",
            "keutamaan": d.get("urgency", "Normal"),
            "bukti_imej": f"evidence/defect_{d['id']}.jpg"
        }

        # 2️⃣ ONLY Homeowner gets remarks
        if role == "Homeowner" and d.get("remarks"):
            defect_item["ulasan"] = d["remarks"]

        # 3️⃣ Append ONCE
        report_defects.append(defect_item)

    return report_defects


# ==================================================
# ROLE CONTEXT (VERY IMPORTANT FOR AI)
# ==================================================

def build_role_context(role):
    if role == "Homeowner":
        return {
            "tajuk_laporan": "Laporan Tuntutan Kecacatan Defect Liability Period (DLP)",
            "tujuan": (
                "Laporan ini disediakan bagi merumuskan kecacatan yang "
                "berlaku dalam tempoh Defect Liability Period (DLP) "
                "untuk rujukan Tribunal."
            )
        }

    if role == "Developer":
        return {
            "tajuk_laporan": "Laporan Pematuhan Pembaikan Defect Liability Period (DLP)",
            "tujuan": (
                "Laporan ini disediakan untuk menunjukkan status pembaikan "
                "dan pematuhan pemaju terhadap kecacatan yang dilaporkan."
            )
        }

    # Legal / Tribunal
    return {
        "tajuk_laporan": "Laporan Gambaran Keseluruhan Pematuhan Defect Liability Period (DLP)",
        "tujuan": (
            "Laporan ini disediakan sebagai gambaran keseluruhan status "
            "kecacatan dan pematuhan untuk rujukan Tribunal."
        )
    }


# ==================================================
# FINAL REPORT DATA (SEND THIS TO AI)
# ==================================================

def build_report_data(role, defects, stats):
    return {
        "maklumat_kes": TRIBUNAL_CASE,
        "pihak_yang_menuntut": PIHAK_YANG_MENUNTUT,
        "penentang": PENENTANG,
        "konteks_peranan": build_role_context(role),
        "ringkasan_statistik": build_summary_stats(stats),
        "senarai_kecacatan": build_defect_list(defects, role),
        "nota_penting": (
            "Laporan ini dijana oleh sistem sebagai dokumen sokongan "
            "kepada Borang 1 Tribunal Tuntutan Pengguna Malaysia (TTPM)."
        )
    }
