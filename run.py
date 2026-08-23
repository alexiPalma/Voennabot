import asyncio
import bot
from security_patches import install


async def main():
    await install(bot)
    await bot.main()


if __name__ == '__main__':
    asyncio.run(main())
