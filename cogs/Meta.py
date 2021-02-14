import discord
import random
import pytesseract
import cv2
import numpy as np
import datetime
import typing
import textwrap

from discord.ext import commands, menus

from utils import utils
from utils.classes import CustomContext
from config import config

MAX_FILESIZE = 100_000
TODO_TASK_LENGTH = 200
TODO_LIST_LENGTH = 100
pytesseract.pytesseract.tesseract_cmd = config["tesseract_path"]


class Meta(commands.Cog):
    """
    Commands that don't belong to any specific category.
    """
    @commands.command()
    async def mystbin(self, ctx: CustomContext, *, text: str = None):
        """
        Paste text or a text file to https://mystb.in.

        `text` - The text to paste to mystbin.
        """
        if not text and not ctx.message.attachments:
            return await ctx.send("No text or text file provided.")
        data = []
        if text:
            data.append(text)
        if ctx.message.attachments:
            data.append("\n\nATTACHMENTS\n\n")
            for attachment in ctx.message.attachments:
                if attachment.height or attachment.width:
                    return await ctx.send("Only text files can be used.")
                if attachment.size > MAX_FILESIZE:
                    return await ctx.send(f"File is too large (>{MAX_FILESIZE}kb).")
                data.append((await attachment.read()).decode(encoding="utf-8"))
        data = "".join(data)
        embed = discord.Embed(
            title="Paste Successful!",
            description=f"[Click here to view]({await ctx.bot.mystbin(data)})",
            colour=ctx.bot.embed_colour,
            timestamp=ctx.message.created_at)
        await ctx.send(embed=embed)

    @commands.command()
    async def hastebin(self, ctx: CustomContext, *, text: str = None):
        """
        Paste text or a text file to https://hastebin.com.

        `text` - The text to paste to hastebin.
        """
        if not text and not ctx.message.attachments:
            return await ctx.send("No text or text file provided.")
        data = []
        if text:
            data.append(text)
        if ctx.message.attachments:
            data.append("\n\nATTACHMENTS\n\n")
            for attachment in ctx.message.attachments:
                if attachment.height or attachment.width:
                    return await ctx.send("Only text files can be used.")
                if attachment.size > MAX_FILESIZE:
                    return await ctx.send(f"File is too large (>{MAX_FILESIZE}kb).")
                data.append((await attachment.read()).decode(encoding="utf-8"))
        data = "".join(data)
        embed = discord.Embed(
            title="Paste Successful!",
            description=f"[Click here to view]({await ctx.bot.hastebin(data)})",
            colour=ctx.bot.embed_colour,
            timestamp=ctx.message.created_at)
        await ctx.send(embed=embed)

    @commands.command()
    async def xkcd(self, ctx: CustomContext, query: typing.Union[int, str] = None):
        """
        View comics from https://xkcd.com. Query by number or title.

        `query` - The comic to search for. Defaults to a random number.
        """
        async with ctx.typing():
            if isinstance(query, str):
                async with ctx.bot.session.get(
                        "https://www.explainxkcd.com/wiki/api.php",
                        params={"action": "query", "list": "search", "format": "json", "srsearch": query,
                                "srwhat": "title", "srlimit": "max"}) as resp:
                    r = await resp.json()
                    if result := r["query"]["search"]:
                        num = result[0]["title"].split(":")[0]
                    else:
                        return await ctx.send("Couldn't find a comic with that query.")
            elif isinstance(query, int):
                num = query
            else:
                async with ctx.bot.session.get("https://xkcd.com/info.0.json") as resp:
                    max_num = (await resp.json())["num"]
                num = random.randint(1, max_num)

            async with ctx.bot.session.get(f"https://xkcd.com/{num}/info.0.json") as resp:
                if resp.status in range(400, 500):
                    return await ctx.send("Couldn't find a comic with that number.")
                elif resp.status >= 500:
                    return await ctx.send("Server error.")
                data = await resp.json()

            embed = discord.Embed(
                title=f"{data['safe_title']} (Comic Number `{data['num']}`)",
                description=data["alt"],
                timestamp=datetime.datetime(year=int(data["year"]), month=int(data["month"]), day=int(data["day"])),
                colour=ctx.bot.embed_colour)
            embed.set_image(url=data["img"])
            embed.set_footer(text="Created:")
            await ctx.send(embed=embed)

    def _ocr(self, bytes_):
        img = cv2.imdecode(np.fromstring(bytes_, np.uint8), 1)
        return pytesseract.image_to_string(img)

    @commands.command()
    async def ocr(self, ctx: CustomContext):
        """
        Read the contents of an attachment using `pytesseract`.
        **NOTE:** This can be *very* inaccurate at times.
        """
        if not ctx.message.attachments:
            return await ctx.send("No attachment provided.")
        ocr_result = await ctx.bot.loop.run_in_executor(None, self._ocr, await ctx.message.attachments[0].read())
        await ctx.send(f"Text to image result for **{ctx.author}**\n```{ocr_result}```")

    @commands.command()
    async def ascii(self, ctx: CustomContext, *, text: str):
        """
        Convert text to ascii characters. Might look messed up on mobile.

        `text` - The text to convert to ascii.
        """
        char_list = textwrap.wrap(text, 25)
        ascii_char_list = [ctx.bot.figlet.renderText(char) for char in char_list]
        await menus.MenuPages(source=utils.PaginatorSource(ascii_char_list, per_page=1), delete_message_after=True).start(ctx)

    @commands.command()
    async def owoify(self, ctx: CustomContext, *, text: str):
        """
        Owoifies text. Mentions are escaped.

        `text` - The text to owoify.
        """
        await ctx.send(discord.utils.escape_mentions(utils.owoify(text)))

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx: CustomContext):
        """
        View the tasks in your todo list.
        """
        entries = await ctx.bot.cache.get_todo(ctx.author.id) or []
        li = [(number, item) for number, item in enumerate(entries, start=1)]
        await menus.MenuPages(utils.TodoSource(li), delete_message_after=True).start(ctx)

    @todo.command()
    async def add(self, ctx: CustomContext, *, task: str):
        """
        Add a task to your todo list.

        `task` - The task to add.
        """
        if len(task) > TODO_TASK_LENGTH:
            return await ctx.send(f"{ctx.bot.emoji_dict['red_tick']} Task is too long (>{TODO_TASK_LENGTH} characters).")

        tasks = await ctx.bot.cache.get_todo(ctx.author.id)
        if tasks is None:
            await ctx.bot.cache.create_todo(ctx.author.id)
        else:
            if len(tasks) >= TODO_TASK_LENGTH:
                return await ctx.send(f"{ctx.bot.emoji_dict['red_tick']} Sorry, you can only have {TODO_TASK_LENGTH} tasks in your todo list at a time.")
            if task in tasks:
                return await ctx.send(f"{ctx.bot.emoji_dict['red_tick']} That task is already in your todo list.")

        await ctx.bot.cache.add_todo(ctx.author.id, task)
        await ctx.send(f"{ctx.bot.emoji_dict['green_tick']} Added `{task}` to your todo list.")

    @todo.command()
    async def remove(self, ctx: CustomContext, *, task: str):
        """
        Remove a task from your todo list.

        `task` - The task to remove. Can be the task number or the task name.
        """
        tasks = await ctx.bot.cache.get_todo(ctx.author.id)

        if not tasks:
            return await ctx.send(f"{ctx.bot.emoji_dict['red_tick']} Your todo list is empty.")
        # try with number
        try:
            task = tasks[int(task) - 1]
            await ctx.bot.cache.remove_todo(ctx.author.id, task)
        except (IndexError, ValueError):
            # try with name
            if task not in tasks:
                return await ctx.send(f"{ctx.bot.emoji_dict['red_tick']} Couldn't find a task with that name or number.")
            await ctx.bot.cache.remove_todo(ctx.author.id, task)

        await ctx.send(f"{ctx.bot.emoji_dict['green_tick']} Removed `{task}` from your todo list.")


def setup(bot):
    bot.add_cog(Meta())
