import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument
import os 
from config import BOT_TOKEN, API_HASH, API_ID, SOURCE_CHAT_ID, TARGET_CHAT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


client = TelegramClient('forward_bot', API_ID, API_HASH)

class MessageForwarder:
    def __init__(self):
        self.processed_messages = set()
        self.is_running = False

    async def get_all_messages(self, chat_id):
        """Рекурсивно получает все сообщения из чата"""
        try:
            messages = []
            async for message in client.iter_messages(chat_id, reverse=True):
                if message.id not in self.processed_messages:
                    messages.append(message)
                    self.processed_messages.add(message.id)
            return messages
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений: {e}")
            return []

    async def forward_message(self, message, target_chat_id):
        """Пересылает сообщение в целевой чат"""
        try:
            # Проверяем тип сообщения и пересылаем соответствующим образом
            if message.media:
                if isinstance(message.media, MessageMediaPhoto):
                    await client.send_file(target_chat_id, message.media, caption=message.text)
                elif isinstance(message.media, MessageMediaDocument):
                    await client.send_file(target_chat_id, message.media, caption=message.text)
                else:
                    await client.send_message(target_chat_id, message.text)
            else:
                await client.send_message(target_chat_id, message.text)
            
            logger.info(f"Сообщение {message.id} переслано успешно")
            await asyncio.sleep(1)  # Задержка чтобы не получить ограничение от Telegram
            
        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения {message.id}: {e}")

    async def forward_all_messages(self):
        """Пересылает все сообщения из исходного чата в целевой"""
        if self.is_running:
            logger.info("Процесс пересылки уже запущен")
            return

        self.is_running = True
        logger.info("Начало пересылки сообщений...")

        try:
            messages = await self.get_all_messages(SOURCE_CHAT_ID)
            total_messages = len(messages)
            logger.info(f"Найдено {total_messages} сообщений для пересылки")

            for i, message in enumerate(messages, 1):
                if not self.is_running:
                    break
                    
                await self.forward_message(message, TARGET_CHAT_ID)
                logger.info(f"Прогресс: {i}/{total_messages} ({i/total_messages*100:.1f}%)")
                
        except Exception as e:
            logger.error(f"Ошибка в процессе пересылки: {e}")
        finally:
            self.is_running = False
            logger.info("Процесс пересылки завершен")

    async def start_realtime_forwarding(self):
        """Запускает пересылку новых сообщений в реальном времени"""
        @client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
        async def handler(event):
            if event.message.id not in self.processed_messages:
                await self.forward_message(event.message, TARGET_CHAT_ID)
                self.processed_messages.add(event.message.id)

forwarder = MessageForwarder()

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Обработчик команды /start"""
    await event.reply(
        "🤖 Бот для пересылки сообщений\n\n"
        "Команды:\n"
        "/forward_all - Переслать все сообщения\n"
        "/start_realtime - Запустить пересылку в реальном времени\n"
        "/stop - Остановить пересылку\n"
        "/status - Статус бота"
    )

@client.on(events.NewMessage(pattern='/forward_all'))
async def forward_all_handler(event):
    """Обработчик команды для пересылки всех сообщений"""
    if forwarder.is_running:
        await event.reply("❌ Процесс пересылки уже запущен!")
        return
    
    await event.reply("🔄 Начинаю пересылку всех сообщений...")
    asyncio.create_task(forwarder.forward_all_messages())

@client.on(events.NewMessage(pattern='/start_realtime'))
async def start_realtime_handler(event):
    """Обработчик команды для запуска пересылки в реальном времени"""
    await forwarder.start_realtime_forwarding()
    await event.reply("✅ Режим реального времени активирован!")

@client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    """Обработчик команды для остановки пересылки"""
    forwarder.is_running = False
    await event.reply("⏹️ Пересылка остановлена!")

@client.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    """Обработчик команды для получения статуса"""
    status = "🟢 Запущен" if forwarder.is_running else "🔴 Остановлен"
    await event.reply(f"Статус бота: {status}\nОбработано сообщений: {len(forwarder.processed_messages)}")

async def main():
    """Основная функция"""
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Бот запущен!")
    
    # Получаем информацию о боте
    me = await client.get_me()
    logger.info(f"Бот @{me.username} готов к работе")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Создаем папку для сессий если её нет
    os.makedirs('sessions', exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")



