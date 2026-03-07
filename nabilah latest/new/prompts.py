# prompts.py
import json


# =================================================
# LANGUAGE CONFIGURATIONS
# =================================================
LANGUAGE_CONFIG = {
    "ms": {
        "name": "Bahasa Malaysia",
        "system_instruction": (
            "Anda menjana laporan sokongan untuk Tribunal Tuntutan Pengguna Malaysia. "
            "Gunakan Bahasa Malaysia formal dan berkecuali. "
            "Jangan menambah fakta baharu, jangan membuat kesimpulan undang-undang, "
            "dan jangan menentukan liabiliti atau kesalahan mana-mana pihak."
        ),
        "report_title": "LAPORAN SOKONGAN TRIBUNAL – TEMPOH LIABILITI KECACATAN (DLP)",
        "generated_label": "Tarikh Jana",
        "disclaimer_title": "PENAFIAN AI",
        "disclaimer_text": (
            "Laporan ini dijana dengan bantuan kecerdasan buatan (AI) bagi tujuan "
            "penyusunan dan ringkasan maklumat sahaja. Semua fakta, data dan bukti "
            "adalah berdasarkan rekod yang dikemukakan. Laporan ini tidak "
            "merupakan nasihat undang-undang dan tidak menggantikan penentuan "
            "atau keputusan Tribunal."
        )
    },
    "en": {
        "name": "English",
        "system_instruction": (
            "You are generating a support report for the Malaysia Consumer Claims Tribunal. "
            "Use formal and neutral English. "
            "Do not add new facts, do not make legal conclusions, "
            "and do not determine liability or fault of any party."
        ),
        "report_title": "TRIBUNAL SUPPORT REPORT – DEFECT LIABILITY PERIOD (DLP)",
        "generated_label": "Generated Date",
        "disclaimer_title": "AI DISCLAIMER",
        "disclaimer_text": (
            "This report was generated with the assistance of artificial intelligence (AI) "
            "for the purpose of organizing and summarizing information only. All facts, data, "
            "and evidence are based on submitted records. This report does not constitute "
            "legal advice and does not replace the determination or decision of the Tribunal."
        )
    }
}


# =================================================
# HOMEOWNER PROMPT (BILINGUAL)
# =================================================
def homeowner_prompt(report_data, language="ms"):
    if language == "en":
        # Translate case info to English
        case_info = report_data.get("maklumat_kes", {})
        case_info_en = {
            "tribunal": "Malaysia Consumer Claims Tribunal",
            "state": case_info.get("negeri", ""),
            "claim_number": case_info.get("no_tuntutan", ""),
            "generated_date": case_info.get("tarikh_jana", ""),
            "claim_amount": case_info.get("amaun_tuntutan", ""),
            "document": "Form 1 Supporting Document"
        }
        
        # Translate statistics to English
        stats = report_data.get("ringkasan_statistik", {})
        stats_en = {
            "total_defects": stats.get("jumlah_kecacatan", 0),
            "pending": stats.get("belum_diselesaikan", 0),
            "completed": stats.get("telah_diselesaikan", 0),
            "critical": stats.get("kritikal", 0)
        }
        
        # Translate defect list to English
        defects = report_data.get("senarai_kecacatan", [])
        defects_en = []
        for d in defects:
            defects_en.append({
                "defect_id": d.get("id_kecacatan", ""),
                "unit": d.get("unit", ""),
                "description": d.get("keterangan", ""),
                "status": d.get("status", ""),
                "deadline": d.get("tarikh_akhir", ""),
                "overdue": "Yes" if d.get("tertunggak") == "Ya" else "No",
                "priority": d.get("keutamaan", ""),
                "remarks": d.get("ulasan", "")
            })
        
        return f"""
This support report is prepared to support the claim submitted by
the Claimant to the Malaysia Consumer Claims Tribunal (TTPM)
in relation to the Defect Liability Period (DLP).

IMPORTANT INSTRUCTIONS (MUST BE COMPLIED WITH):
1. Use formal administrative English and the writing style of an official Tribunal report.
2. Use passive, objective, and factual sentence structures throughout the report.
3. All statements must be framed strictly based on the records, information, and documents submitted.
4. Do not add any new facts, estimates, assumptions, inferences, or interpretations.
5. Do not make any legal conclusions, assessments of liability, or determinations of fault against any party.
6. Avoid the use of emotional language, personal narratives, or argumentative statements.
7. Use formal Tribunal-style phrases such as:
   - “based on the records submitted”
   - “as reported”
   - “for the purpose of the Tribunal’s consideration”
8. Ensure all defect descriptions, statuses, and remarks are written in formal English.
9. Where specific information is unavailable, clearly state:
   “No further information is recorded.”
10. Do not use any markdown formatting, emphasis symbols, or decorative text.
11. Ensure the report is structured, consistent, and reflects the tone of an official administrative document.

The report shall be written as though it is intended to be filed as
an official supporting document before the Malaysia Consumer Claims Tribunal.

Case Information:
{json.dumps(case_info_en, indent=2, ensure_ascii=False)}

Statistics Summary:
{json.dumps(stats_en, indent=2, ensure_ascii=False)}

Defect List:
{json.dumps(defects_en, indent=2, ensure_ascii=False)}

Write the report in English with these NUMBERED sections (you MUST include the numbers):

Support Report for Claim before the Malaysia Consumer Claims Tribunal (TTPM)

1. Purpose of the Report
[State the purpose of this report as being prepared to support the Claimant’s submission]

2. Summary of Reported Defects
[Provide a summary of the reported defects based on the statistical records]

3. Defect List
[List each defect in the following format:
a. Defect ID [number]:
   Description: [description]
   Unit: [unit]
   Status: [status]
   Priority: [priority]
   Remarks: [remarks, or state “No remarks recorded”]

b. Defect ID [number]:
...]

4. Defects That Have Exceeded the Deadline
[State whether any defects have exceeded the stipulated deadline, or state
“No defects have been reported as having exceeded the deadline.”]

5. Formal Request from the Claimant
[State the formal request submitted to the Tribunal]

6. Conclusion
[The conclusion shall be drafted in a neutral and formal manner, stating that
this support report is prepared solely to summarise and present information
relating to defects reported during the Defect Liability Period (DLP),
based on the records submitted by the Claimant,
for the purpose of reference and consideration by the Malaysia Consumer Claims Tribunal,
without making any determination of fault, liability, or legal decision.]

AI Disclaimer:
This report was generated with the assistance of an artificial intelligence (AI) system
for the purpose of organising and summarising information based on records submitted
by the Claimant. This report is provided solely to present information in a clear
and neutral manner and does not constitute legal advice. The AI system bears no
responsibility for any action taken based on this report, and this report does not
replace or affect the determination or decision of the Malaysia Consumer Claims Tribunal.
""".strip()
    
    # Default: Bahasa Malaysia
    return f"""
Laporan sokongan ini disediakan bagi menyokong tuntutan yang dikemukakan oleh
Pihak Yang Menuntut kepada Tribunal Tuntutan Pengguna Malaysia (TTPM)
berhubung Tempoh Liabiliti Kecacatan (Defect Liability Period – DLP).

ARAHAN PENTING:
Laporan sokongan ini disediakan bagi menyokong tuntutan yang dikemukakan oleh
Pihak Yang Menuntut kepada Tribunal Tuntutan Pengguna Malaysia (TTPM)
berhubung Tempoh Liabiliti Kecacatan (Defect Liability Period – DLP).

ARAHAN PENTING (WAJIB DIPATUHI):
1. Gunakan Bahasa Malaysia formal pentadbiran dan gaya penulisan laporan rasmi Tribunal.
2. Gunakan ayat pasif, objektif, dan berfakta sepanjang laporan.
3. Semua pernyataan hendaklah dirangka berdasarkan rekod, maklumat, dan dokumen yang dikemukakan sahaja.
4. Jangan menambah sebarang fakta baharu, anggaran, inferens, atau andaian.
5. Jangan membuat sebarang kesimpulan undang-undang, penilaian liabiliti, atau penentuan kesalahan mana-mana pihak.
6. Elakkan penggunaan bahasa bersifat emosi, naratif peribadi, atau hujahan.
7. Gunakan istilah seperti:
   - “berdasarkan rekod yang dikemukakan”
   - “seperti yang dilaporkan”
   - “untuk tujuan pertimbangan Tribunal”
8. Pastikan teks ULASAN dipaparkan dalam bahasa yang sama dengan bahasa laporan.
9. Jika maklumat tertentu tidak tersedia, nyatakan secara jelas:
   “Tiada maklumat lanjut direkodkan.”
10. Jangan gunakan sebarang format markdown, simbol penegasan, atau hiasan teks.
11. Susun ayat secara kemas, konsisten, dan menyerupai laporan pentadbiran rasmi.
Laporan hendaklah ditulis seolah-olah ia akan difailkan sebagai
dokumen sokongan rasmi kepada Tribunal Tuntutan Pengguna Malaysia.
12. Jika ulasan tidak diberikan atau hanya menyatakan ketiadaan tindakan, nyatakan secara ringkas dan neutral.

Maklumat Kes:
{json.dumps(report_data.get("maklumat_kes", {}), indent=2, ensure_ascii=False)}

Ringkasan Statistik:
{json.dumps(report_data.get("ringkasan_statistik", {}), indent=2, ensure_ascii=False)}

Senarai Kecacatan:
{json.dumps(report_data.get("senarai_kecacatan", []), indent=2, ensure_ascii=False)}

Tulis laporan dengan format berikut:

Laporan Sokongan Bagi Tuntutan Tribunal Tuntutan Pengguna Malaysia (TTPM)

1. Tujuan Laporan
[Terangkan tujuan laporan ini disediakan bagi menyokong tuntutan Pihak Yang Menuntut]

2. Ringkasan Kecacatan yang Dilaporkan
[Senaraikan ringkasan statistik kecacatan]

3. Senarai Kecacatan
[Senaraikan setiap kecacatan dengan format:
a. Kecacatan ID [nombor]:
   Keterangan: [keterangan]
   Unit: [unit]
   Status: [status]
   Keutamaan: [keutamaan]
   Ulasan: [ulasan jika ada, jika tiada nyatakan "Tiada ulasan dikemukakan"]]

4. Kecacatan yang Telah Melepasi Tarikh Akhir
[Nyatakan jika ada kecacatan yang melepasi tarikh akhir, atau "Tiada kecacatan yang telah melepasi tarikh akhir yang dilaporkan."]

5. Permohonan Rasmi Pihak Yang Menuntut
[Nyatakan permohonan rasmi kepada Tribunal]

6. Penutup
[Penutup hendaklah dirangka secara neutral dan formal dengan menyatakan bahawa
laporan sokongan ini disediakan semata-mata untuk merumuskan dan
mempersembahkan maklumat berkaitan kecacatan yang telah dilaporkan
sepanjang Tempoh Liabiliti Kecacatan (Defect Liability Period),
berdasarkan rekod yang dikemukakan oleh Pihak Yang Menuntut,
untuk tujuan rujukan dan pertimbangan Tribunal Tuntutan Pengguna Malaysia,
tanpa membuat sebarang penentuan kesalahan, liabiliti, atau keputusan undang-undang.]

PENAFIAN AI:
Laporan ini dijana dengan bantuan sistem kecerdasan buatan (AI) bagi tujuan penyusunan dan ringkasan maklumat berdasarkan rekod yang dikemukakan oleh Pihak Yang Menuntut. Laporan ini disediakan untuk memberikan maklumat yang jelas dan berkecuali mengenai kecacatan yang dilaporkan dan tidak boleh dianggap sebagai nasihat undang-undang. Sistem AI tidak bertanggungjawab terhadap sebarang tindakan yang diambil berdasarkan laporan ini dan laporan ini tidak menggantikan penentuan atau keputusan Tribunal Tuntutan Pengguna Malaysia.
""".strip()


# =================================================
# DEVELOPER PROMPT (BILINGUAL)
# =================================================
def developer_prompt(report_data, language="ms"):
    if language == "en":
        # Translate case info to English
        case_info = report_data.get("maklumat_kes", {})
        case_info_en = {
            "tribunal": "Malaysia Consumer Claims Tribunal",
            "state": case_info.get("negeri", ""),
            "claim_number": case_info.get("no_tuntutan", ""),
            "generated_date": case_info.get("tarikh_jana", ""),
            "claim_amount": case_info.get("amaun_tuntutan", ""),
            "document": "Form 1 Supporting Document"
        }
        
        stats = report_data.get("ringkasan_statistik", {})
        stats_en = {
            "total_defects": stats.get("jumlah_kecacatan", 0),
            "pending": stats.get("belum_diselesaikan", 0),
            "completed": stats.get("telah_diselesaikan", 0),
            "critical": stats.get("kritikal", 0)
        }
        
        defects = report_data.get("senarai_kecacatan", [])
        defects_en = []
        for d in defects:
            defects_en.append({
                "defect_id": d.get("id_kecacatan", ""),
                "unit": d.get("unit", ""),
                "description": d.get("keterangan", ""),
                "status": d.get("status", ""),
                "deadline": d.get("tarikh_akhir", ""),
                "overdue": "Yes" if d.get("tertunggak") == "Ya" else "No",
                "priority": d.get("keutamaan", ""),
                "remarks": d.get("ulasan", "")
            })
        
        return f"""
This report is prepared by the Respondent (Developer) for compliance purposes
and as a reference document for the Malaysia Consumer Claims Tribunal (TTPM).

IMPORTANT INSTRUCTIONS (MUST BE COMPLIED WITH):
1. Use formal administrative English and the writing style of an official Tribunal report.
2. Use passive, objective, and factual sentence structures throughout the report.
3. Avoid the use of personal narratives, conversational language, or argumentative statements.
4. Ensure all defect descriptions are written in formal English
   (e.g. “Wall crack in master bedroom”, “Broken tile in bathroom”,
   “Leaking pipe under kitchen sink”, “Faulty electrical wiring in living room”,
   “Balcony sliding door stuck”, “Ceiling water stain near air-conditioner”).
5. Ensure all defect statuses are written consistently in English
   (Pending, In Progress, Completed, Delayed).
6. Do not add any new facts, assumptions, estimates, or explanations beyond the records provided.
7. Do not make any admission of liability, fault, or legal responsibility.
8. Do not use any markdown formatting, emphasis symbols, or decorative text.
9. Ensure the report is neatly structured, professional, and reflects the tone of an official administrative document.

The report shall be written as though it is intended to be filed as
an official compliance document before the Malaysia Consumer Claims Tribunal.

Case Information:
{json.dumps(case_info_en, indent=2, ensure_ascii=False)}

Statistics Summary:
{json.dumps(stats_en, indent=2, ensure_ascii=False)}

Defect List:
{json.dumps(defects_en, indent=2, ensure_ascii=False)}

Write the report in English with these NUMBERED sections (you MUST include the numbers):

Compliance Report for Reference before the Malaysia Consumer Claims Tribunal (TTPM)

1. Purpose of the Report
[State that this report is prepared to fulfil the requirements of TTPM and
to present the status of rectification works undertaken by the Developer.]

2. Repair Work That Have Been Completed
[List completed repairs with letter labels like:
a. Defect ID [number]:
   Description: [description]
   Unit: [unit]
   Completion Date: [date]

b. Defect ID [number]:
...]

3. Repair Work That Is Still Outstanding or Delayed
[List repair works that have not yet been completed using the following format:
a. Defect ID [number]:
   Description: [description]
   Unit: [unit]
   Current Status: [status]
   Scheduled Completion Date: [date]

b. Defect ID [number]:
...]

4. Developer's Commitment Statement
[State the Developer’s commitment to comply with applicable requirements
and to continue undertaking rectification works in accordance with records and schedules.]

5. Conclusion
[State that this compliance report is submitted by the Respondent (Developer)
to summarise the status of rectification works that have been completed and
those that remain ongoing during the Defect Liability Period (DLP),
based on internal records, for the purpose of reference and consideration
by the Malaysia Consumer Claims Tribunal, without any admission of fault,
liability, or legal responsibility.]

AI Disclaimer:
This report was generated with the assistance of an artificial intelligence (AI) system
for the purpose of organising and summarising information based on records provided.
This report is intended solely to present information in a clear and neutral manner
and does not constitute legal advice. The AI system bears no responsibility for any
action taken based on this report, and this report does not replace or affect the
determination or decision of the Malaysia Consumer Claims Tribunal.
""".strip()
    
    # Default: Bahasa Malaysia
    return f"""
Laporan ini disediakan oleh Penentang (Pemaju) bagi tujuan pematuhan
dan sebagai dokumen rujukan kepada Tribunal Tuntutan Pengguna Malaysia (TTPM).

ARAHAN PENTING (WAJIB DIPATUHI):
1. Gunakan Bahasa Malaysia formal pentadbiran dan gaya penulisan laporan rasmi Tribunal.
2. Gunakan ayat pasif, objektif, dan berfakta sepanjang laporan.
3. Elakkan penggunaan bahasa berbentuk naratif peribadi, perbualan, atau hujahan.
4. Pastikan semua keterangan kecacatan dinyatakan dalam Bahasa Malaysia formal
   (contoh: Keretakan dinding di bilik tidur utama, Jubin pecah di bilik air,
   Paip bocor di bawah sinki dapur, Pendawaian elektrik rosak di ruang tamu,
   Pintu gelongsor balkoni tersangkut, Kesan tompokan air pada siling berhampiran penyaman udara).
5. Pastikan semua status kecacatan dinyatakan secara konsisten
   (Belum Selesai, Dalam Proses, Selesai, Tertangguh).
6. Semua pernyataan hendaklah dirangka berdasarkan rekod dan maklumat yang tersedia sahaja.
7. Jangan menambah sebarang fakta baharu, anggaran, inferens, atau penjelasan di luar rekod.
8. Jangan membuat sebarang pengakuan kesalahan, liabiliti, atau tanggungjawab undang-undang.
9. Jangan gunakan sebarang format markdown, simbol penegasan, atau hiasan teks.
10. Pastikan laporan disusun secara kemas, konsisten, dan menyerupai dokumen pentadbiran rasmi.

Laporan ini hendaklah ditulis seolah-olah ia akan difailkan sebagai
dokumen pematuhan rasmi kepada Tribunal Tuntutan Pengguna Malaysia.

Maklumat Kes:
{json.dumps(report_data.get("maklumat_kes", {}), indent=2, ensure_ascii=False)}

Ringkasan Statistik:
{json.dumps(report_data.get("ringkasan_statistik", {}), indent=2, ensure_ascii=False)}

Senarai Kecacatan:
{json.dumps(report_data.get("senarai_kecacatan", []), indent=2, ensure_ascii=False)}

Tulis laporan dengan format berikut:

Laporan Pematuhan Bagi Rujukan Tribunal Tuntutan Pengguna Malaysia (TTPM)

1. Tujuan Laporan
[Nyatakan bahawa laporan ini disediakan bagi memenuhi keperluan Tribunal
dan untuk membentangkan status pelaksanaan kerja pembaikan oleh Pemaju.]

2. Kerja Pembaikan yang Telah Disiapkan
[Senaraikan kerja pembaikan yang telah diselesaikan menggunakan format berikut:
a. ID Kecacatan [nombor]
   Keterangan: [keterangan]
   Unit: [unit]
   Tarikh Siap: [tarikh]

b. ID Kecacatan [nombor]
...]

3. Kerja Pembaikan yang Masih Tertunggak atau Tertunda
[Senaraikan kerja pembaikan yang belum diselesaikan menggunakan format berikut:
a. ID Kecacatan [nombor]
   Keterangan: [keterangan]
   Unit: [unit]
   Tarikh siap: [tarikh]

b. ID Kecacatan [nombor]
...]

4. Kenyataan Komitmen Pemaju
[Nyatakan komitmen Pemaju untuk mematuhi keperluan yang berkenaan
dan untuk meneruskan pelaksanaan kerja pembaikan berdasarkan rekod dan jadual yang tersedia.]

5. Penutup
[Nyatakan bahawa laporan pematuhan ini dikemukakan oleh Penentang (Pemaju)
bagi merumuskan status pelaksanaan kerja pembaikan yang telah disiapkan
dan yang masih berjalan sepanjang Tempoh Liabiliti Kecacatan
(Defect Liability Period),
berdasarkan rekod dalaman yang tersedia,
untuk tujuan rujukan dan pertimbangan oleh Tribunal Tuntutan Pengguna Malaysia,
tanpa sebarang pengakuan kesalahan, liabiliti, atau tanggungjawab undang-undang.]

PENAFIAN AI:
Laporan ini dijana dengan bantuan sistem kecerdasan buatan (AI)
bagi tujuan penyusunan dan ringkasan maklumat berdasarkan rekod yang tersedia.
Laporan ini disediakan semata-mata untuk menyampaikan maklumat secara jelas
dan berkecuali serta tidak boleh dianggap sebagai nasihat undang-undang.
Sistem AI tidak bertanggungjawab terhadap sebarang tindakan yang diambil
berdasarkan laporan ini dan laporan ini tidak menggantikan penentuan
atau keputusan Tribunal Tuntutan Pengguna Malaysia.
""".strip()


# =================================================
# LEGAL / TRIBUNAL PROMPT (BILINGUAL)
# =================================================
def legal_prompt(report_data, language="ms"):
    if language == "en":
        # Translate case info to English
        case_info = report_data.get("maklumat_kes", {})
        case_info_en = {
            "tribunal": "Malaysia Consumer Claims Tribunal",
            "state": case_info.get("negeri", ""),
            "claim_number": case_info.get("no_tuntutan", ""),
            "generated_date": case_info.get("tarikh_jana", ""),
            "claim_amount": case_info.get("amaun_tuntutan", ""),
            "document": "Form 1 Supporting Document"
        }
        
        stats = report_data.get("ringkasan_statistik", {})
        stats_en = {
            "total_defects": stats.get("jumlah_kecacatan", 0),
            "pending": stats.get("belum_diselesaikan", 0),
            "completed": stats.get("telah_diselesaikan", 0),
            "critical": stats.get("kritikal", 0)
        }
        
        defects = report_data.get("senarai_kecacatan", [])
        defects_en = []
        for d in defects:
            defects_en.append({
                "defect_id": d.get("id_kecacatan", ""),
                "unit": d.get("unit", ""),
                "description": d.get("keterangan", ""),
                "status": d.get("status", ""),
                "deadline": d.get("tarikh_akhir", ""),
                "overdue": "Yes" if d.get("tertunggak") == "Ya" else "No",
                "priority": d.get("keutamaan", ""),
                "remarks": d.get("ulasan", "")
            })
        
        return f"""
This report is prepared for the purpose of providing an objective and neutral
overview of the current level of compliance with the
Defect Liability Period (DLP),
for reference by the Malaysia Consumer Claims Tribunal,
based on the records and information submitted.

IMPORTANT INSTRUCTIONS (MUST BE COMPLIED WITH):
1. Use formal administrative English and the writing style of a Tribunal reference document.
2. Use passive, objective, concise, and factual sentence structures throughout the report.
3. Avoid the use of personal narratives, conversational language, or argumentative statements.
4. All statements must be strictly based on records, information, and documents submitted.
5. Do not add any new facts, estimates, assumptions, interpretations, or inferences.
6. Do not make any determination of fault, liability, or legal responsibility.
7. Do not make any legal conclusions, findings, or recommendations.
8. Do not use any markdown formatting, emphasis symbols, or decorative text.
9. Ensure the report is structured, consistent, and reflects the tone of an official administrative reference document.

This report shall be written as though it is intended to be filed as
an official reference document before the Malaysia Consumer Claims Tribunal.

Case Information:
{json.dumps(case_info_en, indent=2, ensure_ascii=False)}

Statistics Summary:
{json.dumps(stats_en, indent=2, ensure_ascii=False)}

Defect List:
{json.dumps(defects_en, indent=2, ensure_ascii=False)}

Write the report in English with these NUMBERED sections (you MUST include the numbers):

Overview Report on Defect Liability Period (DLP) Compliance

1. Case Background
[Briefly state the case information, including the claim reference number,
claim amount, and the total number of recorded defects,
based on the submitted documents.]

2. Current Position of Defect Records
[Briefly state the current status of defects based on records,
including the number of defects completed and those remaining outstanding,
without technical elaboration.]

3. Observations on Status and Timeframes
[State objective observations regarding defects recorded as outstanding
or having exceeded the stipulated timeframe, if any,
without attributing fault, liability, or responsibility to any party.]

4. Notes for Tribunal Consideration
[State that the information is presented for the purpose of Tribunal reference
and consideration based on available records,
without any recommendation or determination.]

5. Summary
[State that this reference report is prepared to summarise the current position
of compliance with the Defect Liability Period (DLP)
based on the records submitted,
and does not contain any determination of fault, liability,
or legal decision.]

AI Disclaimer:
This reference report was generated with the assistance of an artificial intelligence (AI) system
for the purpose of organising and summarising information based on submitted records.
This report is provided solely for Tribunal reference and informational purposes
and does not constitute legal advice.
This report does not replace or affect the determination or decision
of the Malaysia Consumer Claims Tribunal.
""".strip()
    
    # Default: Bahasa Malaysia
    return f"""
Laporan ini disediakan bagi tujuan memberikan gambaran keseluruhan
secara objektif dan berkecuali berhubung tahap pematuhan
Tempoh Liabiliti Kecacatan (Defect Liability Period – DLP)
untuk rujukan Tribunal Tuntutan Pengguna Malaysia.

ARAHAN PENTING (WAJIB DIPATUHI):
1. Gunakan Bahasa Malaysia formal pentadbiran dan gaya penulisan laporan rasmi Tribunal.
2. Gunakan ayat pasif, objektif, dan berfakta sepanjang laporan.
3. Elakkan penggunaan bahasa berbentuk naratif peribadi, perbualan, atau hujahan.
4. Semua pernyataan hendaklah dirangka berdasarkan rekod, maklumat,
   dan dokumen yang dikemukakan sahaja.
5. Jangan menambah sebarang fakta baharu, anggaran, inferens,
   tafsiran, atau penjelasan di luar rekod yang tersedia.
6. Jangan membuat sebarang penentuan kesalahan, liabiliti,
   atau tanggungjawab undang-undang.
7. Jangan membuat sebarang kesimpulan atau syor undang-undang.
8. Jangan gunakan sebarang format markdown, simbol penegasan,
   atau hiasan teks.
9. Pastikan laporan disusun secara kemas, konsisten,
   dan menyerupai dokumen pentadbiran rasmi.

Laporan ini hendaklah ditulis seolah-olah ia akan difailkan sebagai
dokumen rujukan rasmi kepada Tribunal Tuntutan Pengguna Malaysia.

Maklumat Kes:
{json.dumps(report_data.get("maklumat_kes", {}), indent=2, ensure_ascii=False)}

Ringkasan Statistik:
{json.dumps(report_data.get("ringkasan_statistik", {}), indent=2, ensure_ascii=False)}

Senarai Kecacatan:
{json.dumps(report_data.get("senarai_kecacatan", []), indent=2, ensure_ascii=False)}

Tulis laporan dengan format berikut:

Laporan Gambaran Keseluruhan Pematuhan Tempoh Liabiliti Kecacatan (DLP)

1. Latar Belakang Kes
[Nyatakan secara ringkas maklumat kes termasuk nombor tuntutan,
amaun tuntutan, dan jumlah kecacatan yang direkodkan,
berdasarkan dokumen yang dikemukakan.]

2. Kedudukan Semasa Rekod Kecacatan
[Nyatakan secara ringkas status kecacatan berdasarkan rekod,
termasuk jumlah yang telah diselesaikan dan yang masih belum diselesaikan,
tanpa perincian teknikal.]

3. Pemerhatian Berkaitan Status dan Tempoh
[Nyatakan pemerhatian berkaitan kecacatan yang direkodkan sebagai
masih tertunggak atau melepasi tempoh, jika ada,
tanpa mengaitkan sebarang kesalahan atau tanggungjawab.]

4. Nota Untuk Pertimbangan Tribunal
[Nyatakan bahawa maklumat ini dibentangkan untuk rujukan dan pertimbangan Tribunal
berdasarkan rekod yang tersedia, tanpa sebarang syor atau penentuan.]

5. Rumusan
[Nyatakan bahawa laporan rujukan ini disediakan bagi merumuskan
kedudukan semasa pematuhan Tempoh Liabiliti Kecacatan (DLP)
berdasarkan rekod yang dikemukakan,
dan tidak mengandungi sebarang penentuan kesalahan, liabiliti,
atau keputusan undang-undang.]

PENAFIAN AI
Laporan rujukan ini dijana dengan bantuan sistem kecerdasan buatan (AI)
bagi tujuan penyusunan dan ringkasan maklumat berdasarkan rekod yang dikemukakan.
Laporan ini disediakan semata-mata untuk tujuan rujukan Tribunal
dan tidak boleh dianggap sebagai nasihat undang-undang.
Laporan ini tidak menggantikan penentuan atau keputusan
Tribunal Tuntutan Pengguna Malaysia.
""".strip()


# =================================================
# PROMPT SELECTOR (BILINGUAL SUPPORT)
# =================================================
def build_prompt(role, report_data, language="ms"):
    """
    Pemilih prompt berdasarkan peranan pengguna dan bahasa
    Select prompt based on user role and language
    
    Args:
        role: "Homeowner", "Developer", or "Legal"
        report_data: Dictionary containing case information
        language: "ms" for Bahasa Malaysia, "en" for English
    """
    if role == "Homeowner":
        return homeowner_prompt(report_data, language)
    elif role == "Developer":
        return developer_prompt(report_data, language)
    else:
        return legal_prompt(report_data, language)


def get_language_config(language="ms"):
    """
    Get language-specific configuration
    """
    return LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["ms"])
