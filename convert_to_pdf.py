import docx
import pymupdf

def convert_docx_to_pdf(docx_path, pdf_path):
    doc_word = docx.Document(docx_path)
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842) # A4

    text_parts = []
    for p in doc_word.paragraphs:
        if p.text.strip():
            text_parts.append(p.text.strip())

    full_text = "\n\n".join(text_parts)
    rect = pymupdf.Rect(45, 50, 550, 800)
    page.insert_textbox(rect, full_text, fontsize=10, fontname="helv")

    pdf.save(pdf_path)
    pdf.close()
    print(f"Generated uploadable PDF version: {pdf_path}")

convert_docx_to_pdf("NeuralDocs_End_to_End_Guide.docx", "NeuralDocs_End_to_End_Guide.pdf")
