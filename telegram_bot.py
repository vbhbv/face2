import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode 

# 1. تحميل متغيرات البيئة (يعمل محلياً، لكن يجب استخدام متغيرات Railway)
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
    await update.message.reply_text('مرحباً! أنا جاهز لتحميل الفيديوهات. أرسل لي رابط فيديو من فيسبوك.')

async def handle_facebook_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الروابط وإرسال الفيديو كملف مُتدفق."""
    link = update.message.text
    
    if not link or "facebook.com" not in link:
        await update.message.reply_text('الرجاء إرسال رابط صحيح لفيديو من فيسبوك.')
        return

    # إرسال رسالة انتظار فورية وحذفها لاحقاً
    wait_message = await update.message.reply_text('⏳ جارٍ تحليل الرابط بواسطة خدمة Railway... قد يستغرق الأمر بعض الوقت لإتمام الإرسال.')

    try:
        # 1. الاتصال بخدمة API الخلفية
        response = requests.post(API_URL, json={"facebook_url": link}, timeout=45)
        response.raise_for_status()

        data = response.json()
        
        if data.get("status") == "success" and data.get("direct_download_url"):
            
            title = data.get("title", "الفيديو المطلوب")
            direct_url = data.get("direct_download_url")
            duration = data.get("duration", 0) # قراءة المدة الزمنية
            
            try:
                # 2. الإرسال السحابي المتدفق (حل مشكلة الحجم والسرعة)
                await update.message.reply_video(
                    video=direct_url, 
                    caption=f"✅ تم التحميل: {title}",
                    duration=duration, 
                    supports_streaming=True # هام لتحسين معالجة الملفات الكبيرة
                )
                
                # 3. حذف رسالة الانتظار
                await wait_message.delete()
                
            except Exception as upload_e:
                # في حالة فشل تليجرام في سحب الملف
                logger.error(f"فشل إرسال الفيديو كملف: {upload_e}")
                await wait_message.delete()
                await update.message.reply_text(
                    f"⚠️ فشل إرسال الفيديو كملف. يمكنك التنزيل عبر الرابط المباشر:\n`{direct_url}`",
                    parse_mode='Markdown'
                )

        else:
            await wait_message.delete()
            await update.message.reply_text(f"❌ فشل تحليل الفيديو: {data.get('detail', 'خطأ غير معروف في الخدمة الخلفية.')}")

    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في الاتصال بالـ API الخلفية: {e}")
        await wait_message.delete()
        await update.message.reply_text('⚠️ تعذر الاتصال بخدمة التنزيل الآن. حاول لاحقاً.')
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        await wait_message.delete()
        await update.message.reply_text('⚠️ حدث خطأ غير متوقع أثناء المعالجة.')


def main() -> None:
    """تشغيل البوت."""
    if not BOT_TOKEN or not API_URL:
        logger.error("🚫 لم يتم العثور على متغيرات البيئة BOT_TOKEN أو FACEBOOK_VIDEO_API_URL. الرجاء التأكد من إضافتها يدوياً في إعدادات Railway.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_facebook_link))

    logger.info("✅ تم تشغيل البوت بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
