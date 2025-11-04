import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode 

# تحميل متغيرات البيئة
load_dotenv() 

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("FACEBOOK_VIDEO_API_URL")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('مرحباً! أنا جاهز لتحميل الفيديوهات. أرسل لي رابط فيديو من فيسبوك.')

async def handle_facebook_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الروابط وإرسال الفيديو كملف مُتدفق."""
    link = update.message.text
    
    if not link or "facebook.com" not in link:
        await update.message.reply_text('الرجاء إرسال رابط صحيح لفيديو من فيسبوك.')
        return

    wait_message = await update.message.reply_text('⏳ جارٍ تحليل الرابط بواسطة خدمة Railway... جاري تجاوز عقبات فيسبوك.')

    try:
        # 1. الاتصال بخدمة API الخلفية
        response = requests.post(API_URL, json={"facebook_url": link}, timeout=45)
        response.raise_for_status()

        data = response.json()
        
        if data.get("status") == "success" and data.get("direct_download_url"):
            
            title = data.get("title", "الفيديو المطلوب")
            direct_url = data.get("direct_download_url")
            duration = data.get("duration", 0)
            ext = data.get("ext", "mp4")
            
            # رأسيات محاكاة للمتصفح (لتفادي حظر فيسبوك)
            tele_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            try:
                # 2. الإرسال السحابي المتدفق مع رأسيات (لمزيد من القوة)
                await update.message.reply_video(
                    video=direct_url, 
                    caption=f"✅ تم التحميل بنجاح: {title}",
                    duration=duration, 
                    supports_streaming=True,
                    filename=f"{title}.{ext}", # لضمان الامتداد الصحيح
                    read_timeout=90, # زيادة مهلة القراءة لتليجرام
                    api_kwargs={'headers': tele_headers} # <--- الإضافة الجديدة
                )
                
                # 3. حذف رسالة الانتظار
                await wait_message.delete()
                
            except Exception as upload_e:
                logger.error(f"فشل إرسال الفيديو كملف: {upload_e}")
                await wait_message.delete()
                await update.message.reply_text(
                    f"⚠️ فشل إرسال الفيديو كملف. يمكنك التنزيل عبر الرابط المباشر:\n`{direct_url}`",
                    parse_mode='MarkdownV2'
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
    if not BOT_TOKEN or not API_URL:
        logger.error("🚫 لم يتم العثور على متغيرات البيئة BOT_TOKEN أو FACEBOOK_VIDEO_API_URL.")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_facebook_link))
    logger.info("✅ تم تشغيل البوت بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
