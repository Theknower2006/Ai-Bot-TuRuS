import os
from dotenv import load_dotenv
load_dotenv()
import openai
import pytesseract
from PIL import Image
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader
import docx

# إعداد مفاتيح البيئة
openai.api_key = os.getenv("OPENAI_API_KEY")
user_docs = {}

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل لي ملف PDF أو صورة أو Word وسأقوم بقراءته والرد على أسئلتك!")

# تحميل الملف وتخزينه
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = await update.message.document.get_file()
    file_path = f"user_files/{user_id}_{update.message.document.file_name}"
    await file.download_to_drive(file_path)
    extracted_text = ""

    if file_path.endswith('.pdf'):
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted_text += page.extract_text()
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            extracted_text += para.text + "\n"

    user_docs[user_id] = extracted_text
    await update.message.reply_text("تم حفظ الملف بنجاح! يمكنك الآن طرح أي سؤال عليه.")

# معالجة الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = await update.message.photo[-1].get_file()
    file_path = f"user_files/{user_id}_image.jpg"
    await photo.download_to_drive(file_path)
    text = pytesseract.image_to_string(Image.open(file_path))
    user_docs[user_id] = text
    await update.message.reply_text("تم مسح الصورة ضوئيًا وحفظ محتواها! اسأل ما تريد.")

# الرد على الأسئلة بناءً على المحتوى المخزن
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_docs:
        await update.message.reply_text("رجاءً أرسل ملفًا أو صورة أولاً.")
        return

    prompt = f"اقرأ المحتوى التالي ثم أجب على السؤال:

{user_docs[user_id]}

السؤال: {update.message.text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    await update.message.reply_text(response.choices[0].message.content.strip())

# مسح الذاكرة
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_docs:
        del user_docs[user_id]
        await update.message.reply_text("تم مسح الملف المخزن.")
    else:
        await update.message.reply_text("لا يوجد ملف مخزن لمسحه.")

# عدد المستخدمين
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"عدد المستخدمين الذين قاموا برفع ملفات: {len(user_docs)}")

app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("users", users))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
