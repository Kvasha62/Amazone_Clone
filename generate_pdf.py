import weasyprint

html_path = '/home/user/TEXTBOOK.html'
pdf_path = '/home/user/TEXTBOOK.pdf'

doc = weasyprint.HTML(filename=html_path)
doc.write_pdf(pdf_path)
print(f"PDF created: {pdf_path}")
