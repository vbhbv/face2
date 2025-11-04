import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. تحميل متغيرات البيئة
load_dotenv() 

# 2. قراءة متغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("FACEBOOK_VIDEO_API_URL")

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- وظائف البوت ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على أمر /start."""
    await update.message.reply_text('مرحباً! أنا جاهز لتحميل الفيديوهات. أرسل لي رابط فيديو من فيسبوك.')

async def handle_facebook_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الروابط وإرسالها إلى الـ API الخلفية."""
    link = update.message.text
    
    if not link or "facebook.com" not in link:
        await update.message.reply_text('الرجاء إرسال رابط صحيح لفيديو من فيسبوك.')
        return

    await update.message.reply_text('⏳ جارٍ تحليل الرابط بواسطة خدمة Railway...')

    try:
        # الاتصال بخدمة API الخلفية
        response = requests.post(
            API_URL, 
            json={"facebook_url": link},
            timeout=45 # مهلة كافية
        )
        response.raise_for_status() # إلقاء استثناء لأكواد 4xx/5xx

        data = response.json()
        
        if data.get("status") == "success" and data.get("direct_download_url"):
            title = data.get("title", "الفيديو المطلوب")
            direct_url = data.get("direct_download_url")

            reply_message = (
                f"✅ **{title}**\n\n"
                f"رابط التنزيل المباشر (اضغط لفتح): \n"
                f"`{direct_url}`"
            )
            await update.message.reply_text(reply_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ فشل تحليل الفيديو: {data.get('detail', 'خطأ غير معروف في الخدمة الخلفية.')}")

    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في الاتصال بالـ API الخلفية: {e}")
        await update.message.reply_text('⚠️ تعذر الاتصال بخدمة التنزيل على Railway. حاول لاحقاً.')
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        await update.message.reply_text('⚠️ حدث خطأ غير متوقع أثناء المعالجة.')


def main() -> None:
    """تشغيل البوت."""
    if not BOT_TOKEN or not API_URL:
        logger.error("🚫 لم يتم العثور على متغيرات البيئة BOT_TOKEN أو FACEBOOK_VIDEO_API_URL. الرجاء التحقق من ملف .env.")
        return

    # بناء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_facebook_link))

    logger.info("✅ تم تشغيل البوت بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
