import os
import tempfile
from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from docx2pdf import convert as docx2pdf_convert
from pdf2docx import Converter
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8442613132:AAE8IOa98wiSxzWh0Tkph7E6v7rx8jRHQmA"

# --- Helpers ---
async def convert_image_to_pdf(file_path):
    im = Image.open(file_path).convert("RGB")
    pdf_path = file_path.rsplit(".", 1)[0] + ".pdf"
    im.save(pdf_path)
    return pdf_path

async def merge_pdfs(file_paths):
    merger = PdfMerger()
    for f in file_paths:
        merger.append(f)
    merged_path = "merged.pdf"
    merger.write(merged_path)
    merger.close()
    return merged_path

async def split_pdf(file_path):
    reader = PdfReader(file_path)
    output_files = []
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        out_path = f"page_{i+1}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        output_files.append(out_path)
    return output_files

async def compress_pdf(file_path):
    reader = PdfReader(file_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out_path = "compressed.pdf"
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path

async def word_to_pdf(file_path):
    out_path = file_path.rsplit(".", 1)[0] + ".pdf"
    docx2pdf_convert(file_path, out_path)
    return out_path

async def pdf_to_word(file_path):
    out_path = file_path.rsplit(".", 1)[0] + ".docx"
    cv = Converter(file_path)
    cv.convert(out_path)
    cv.close()
    return out_path

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Welcome to File Converter Bot!\n\n"
        "Send me files and use commands:\n"
        "- /img2pdf (send image)\n"
        "- /merge (send multiple PDFs)\n"
        "- /split (send PDF)\n"
        "- /compress (send PDF)\n"
        "- /doc2pdf (send .docx)\n"
        "- /pdf2doc (send .pdf)\n"
    )

# File receiver (fix octet.stream issue)
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    photo = update.message.photo

    if doc:  # User sent a document
        filename = doc.file_name if doc.file_name else "uploaded_file"
        file = await doc.get_file()
    elif photo:  # User sent an image
        filename = "uploaded.jpg"
        file = await photo[-1].get_file()
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    await file.download_to_drive(custom_path=tmp_path)

    context.user_data["last_file"] = tmp_path
    await update.message.reply_text(f"✅ File received: {filename}\nNow send a command (e.g. /img2pdf, /doc2pdf, /merge)")

async def img2pdf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get("last_file")
    out_path = await convert_image_to_pdf(file_path)
    await update.message.reply_document(
        InputFile(out_path, filename=os.path.basename(out_path))
    )

async def merge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "merge_files" not in context.user_data:
        context.user_data["merge_files"] = []
    file_path = context.user_data.get("last_file")
    context.user_data["merge_files"].append(file_path)
    if len(context.user_data["merge_files"]) >= 2:
        out_path = await merge_pdfs(context.user_data["merge_files"])
        await update.message.reply_document(
            InputFile(out_path, filename=os.path.basename(out_path))
        )
        context.user_data["merge_files"] = []
    else:
        await update.message.reply_text("📌 Upload another PDF or send /merge again.")

async def split_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get("last_file")
    outputs = await split_pdf(file_path)
    for out in outputs:
        await update.message.reply_document(
            InputFile(out, filename=os.path.basename(out))
        )

async def compress_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get("last_file")
    out_path = await compress_pdf(file_path)
    await update.message.reply_document(
        InputFile(out_path, filename=os.path.basename(out_path))
    )

async def doc2pdf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get("last_file")
    out_path = await word_to_pdf(file_path)
    await update.message.reply_document(
        InputFile(out_path, filename=os.path.basename(out_path))
    )

async def pdf2doc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get("last_file")
    out_path = await pdf_to_word(file_path)
    await update.message.reply_document(
        InputFile(out_path, filename=os.path.basename(out_path))
    )

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, file_handler))
    app.add_handler(CommandHandler("img2pdf", img2pdf_cmd))
    app.add_handler(CommandHandler("merge", merge_cmd))
    app.add_handler(CommandHandler("split", split_cmd))
    app.add_handler(CommandHandler("compress", compress_cmd))
    app.add_handler(CommandHandler("doc2pdf", doc2pdf_cmd))
    app.add_handler(CommandHandler("pdf2doc", pdf2doc_cmd))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
