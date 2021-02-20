import discord
import datetime
import re
import subprocess
import typing
import io

from discord.ext import commands, menus
from selenium import webdriver
from selenium.common.exceptions import InvalidArgumentException, WebDriverException

from utils import utils
from utils.classes import CustomContext
from config import config

# constants

SUPPORT_SERVER_ID = 798329404325101600
driver = webdriver.Chrome(config["webdriver_path"])


class Admin(commands.Cog):
    """
    Commands that only my owner can use.
    """
    async def cog_check(self, ctx: CustomContext):
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner
        return True

    @commands.group(invoke_without_command=True, aliases=["adm", "dev", "owner"])
    async def admin(self, ctx: CustomContext):
        """
        Admin commands.
        """

    @admin.command(aliases=["terminate", "stop"])
    async def shutdown(self, ctx: CustomContext):
        """
        Shuts down the bot.
        """
        confirm_embed = utils.EmbedConfirm(discord.Embed(title="Are you sure?", colour=ctx.bot.embed_colour),
                                                   delete_message_after=False)
        confirm = await confirm_embed.prompt(ctx)
        if confirm:
            await confirm_embed.message.edit(
                embed=discord.Embed(
                    title="Logging out now...",
                    colour=ctx.bot.embed_colour,
                    timestamp=datetime.datetime.utcnow()))
            return await ctx.bot.close()
        await confirm_embed.message.delete()

    @admin.command()
    async def load(self, ctx: CustomContext, *cogs):
        """
        Loads cogs.

        `args` - Any amount of cogs to load.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_load = ctx.bot.coglist
        else:
            cogs_to_load = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]

        finished_cogs = []
        for cog in cogs_to_load:
            try:
                ctx.bot.load_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = "\n".join(finished_cogs)
        await ctx.send(f"**Finished Loading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def unload(self, ctx: CustomContext, *cogs):
        """
        Unloads cogs.

        `args` - Any amount of cogs to unload.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_unload = list(ctx.bot.extensions)
        else:
            cogs_to_unload = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]

        try:
            cogs_to_unload.remove("cogs.Admin")  # :^)
        except ValueError:
            pass

        finished_cogs = []
        for cog in cogs_to_unload:
            try:
                ctx.bot.unload_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = "\n".join(finished_cogs)
        await ctx.send(f"**Finished Unloading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def reload(self, ctx: CustomContext, *cogs):
        """
        Reloads cogs.

        `args` - Any amount of cogs to reload.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_reload = list(ctx.bot.extensions)
        else:
            cogs_to_reload = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]
        finished_cogs = []
        for cog in cogs_to_reload:
            try:
                ctx.bot.reload_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = "\n".join(finished_cogs)
        await ctx.send(f"**Finished Reloading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def cleanup(self, ctx: CustomContext, amount: int = 10, limit: int = 100):
        """
        Self-deletes messages in the current channel.

        `amount` - The amount of messages to delete. Defaults to 10.
        `limit` - The amount of messages to search through. Defaults to 100.
        """
        counter = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.id == ctx.bot.user.id:
                await message.delete()
                counter += 1
                if counter >= amount:
                    break
        await ctx.send(f"Successfully purged `{counter}` message(s).")

    @admin.command()
    async def emojisnipe(self, ctx: CustomContext, name: str,
                         emoji: typing.Union[discord.Emoji, discord.PartialEmoji] = None):
        """
        Snipes emojis for personal use.

        `name` - The name of the emoji.
        `emoji` - The emoji to snipe (can NOT be unicode).
        """
        if emoji:
            emoji = await emoji.url.read()
        else:
            if not ctx.message.attachments:
                return await ctx.send("No emoji provided.")
            emoji = await ctx.message.attachments[0].read()
        await ctx.bot.get_guild(SUPPORT_SERVER_ID).create_custom_emoji(name=name, image=emoji)
        await ctx.send("👌")

    @admin.group(invoke_without_command=True)
    async def error(self, ctx: CustomContext):
        """
        View the errors in the database.
        """
        errors = await ctx.bot.pool.fetch("SELECT * FROM errors")
        if not errors:
            return await ctx.send("No errors in the database! 🥳")
        await menus.MenuPages(utils.ErrorSource(errors, per_page=1), delete_message_after=True).start(ctx)

    @error.command()
    async def view(self, ctx: CustomContext, err_num: int):
        """
        View information about an error in the database.

        `err_num` - The error number to search for.
        """
        error = await ctx.bot.pool.fetch(f"SELECT * FROM errors WHERE err_num = $1", err_num)
        if not error:
            return await ctx.send(f"Could not find an error with the number `{err_num}` in the database.")
        await menus.MenuPages(utils.ErrorSource([error], per_page=1)).start(ctx)  # lazy me :p

    @error.command()
    async def fix(self, ctx: CustomContext, error: str):
        """
        Remove an error or errors from the database.

        `error` - The errors to remove from the database.
        """
        if re.match(r"\d+-\d+", error):  # x-x
            rnge = error.split("-")
            for i in range(int(rnge[0]), int(rnge[1]) + 1):
                await ctx.bot.pool.execute("DELETE FROM errors WHERE err_num = $1", i)
            await ctx.send(f"Successfully removed errors `{rnge[0]}` to `{rnge[1]}`.")
        elif error.lower() == "all":
            await ctx.bot.pool.execute("DELETE FROM errors")
            await ctx.send("Thanks for fixing all my errors!")
        elif error.isdigit():
            await ctx.bot.pool.execute("DELETE FROM errors WHERE err_num = $1", int(error))
            await ctx.send("👌")
        else:
            await ctx.send("Invalid option.")

    @admin.command()
    async def sync(self, ctx: CustomContext):
        """
        Syncs code with github and restarts the bot.
        """
        out = subprocess.check_output("git pull", shell=True)
        await ctx.send(f"```{out.decode('utf-8')}```")
        await ctx.message.add_reaction("🔁")
        await ctx.bot.close()  # process manager handles the rest

    # @admin.command(name="eval")
    # async def _eval(self, ctx, *, code: StripCodeblocks):
    #     """
    #     Evaluates code. Inspired by [R. Danny's eval](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L217).
    #
    #     `code` - The code to evaluate.
    #     """
    #     environment = {
    #         "_ctx": ctx,
    #         "_bot": ctx.bot,
    #         "_author": ctx.author,
    #         "_channel": ctx.channel,
    #         "_guild": ctx.guild,
    #         "_message": ctx.message
    #     }
    #     stdout = io.StringIO()
    #     code = textwrap.indent(code, prefix="\t")
    #     eval_func = f"async def eval_func():\n{code}"
    #
    #     try:
    #         exec(eval_func, environment)
    #     except Exception as e:
    #         with suppress(discord.HTTPException):
    #             await ctx.message.add_reaction("❗")
    #         return await ctx.send(f"```py\n{e.__class__.__name__}: {e}```")
    #
    #     eval_func = environment["eval_func"]
    #     try:
    #         with redirect_stdout(stdout):
    #             val = await eval_func()
    #     except Exception as e:
    #         with suppress(discord.HTTPException):
    #             await ctx.message.add_reaction("‼️")
    #         tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    #         return await ctx.author.send(f"```py\n{tb}```")
    #
    #     with suppress(discord.HTTPException):
    #         await ctx.message.add_reaction("✅")
    #     embed = discord.Embed(title="Stdout", description=f"```py\n{stdout.getvalue() or 'None'}```",
    #                           colour=ctx.bot.embed_colour, timestamp=datetime.datetime.now())
    #     embed.add_field(name="Return Value", value=f"```py\n{val or 'None'}```")
    #     await ctx.send(embed=embed)

    @admin.group(invoke_without_command=True)
    async def blacklist(self, ctx: CustomContext):
        """
        Display all blacklisted users.
        """
        data = list(dict(await ctx.bot.pool.fetch("SELECT * FROM blacklisted_users")).items())
        await menus.MenuPages(utils.BlacklistSource(data, per_page=10), delete_message_after=True).start(ctx)

    @blacklist.command()
    async def add(self, ctx: CustomContext, user: discord.User, *, reason: str = None):
        """
        Blacklist a user.

        `user` - The user to blacklist.
        `reason` - The reason why you want to blacklist them (optional).
        """
        reason = reason or "No reason provided."
        await ctx.bot.cache.add_blacklist(user.id, reason=reason)
        await ctx.send("👌")

    @blacklist.command()
    async def remove(self, ctx: CustomContext, *, user: discord.User):
        """
        Removes a user from the blacklist.

        `user` - The user to remove.
        """
        await ctx.bot.cache.remove_blacklist(user.id)
        await ctx.send("👌")

    @admin.command()
    async def sql(self, ctx: CustomContext, option: str, *, query: str):
        """
        Executes a given sql query.

        `option` - The option. Valid options include `execute`, `executemany`, `fetch`, `fetchrow` and `fetchval`.
        `query` - The sql query to execute.
        """
        options = ["execute", "executemany", "fetch", "fetchrow", "fetchval"]
        if (option := option.lower()) not in options:
            options = "\n".join(options)
            return await ctx.send(f"Invalid option provided. Valid options:\n{options}")

        method = getattr(ctx.bot.pool, option)
        try:
            data = await method(query)
        except Exception as e:
            embed = discord.Embed(
                title="Query did not complete successfully",
                description=f"```diff\n-{e.__class__.__name__}: {e}```",
                colour=0xff0000,
                timestamp=datetime.datetime.now())
            return await ctx.send(embed=embed)

        embed = discord.Embed(title="Query completed successfully", colour=ctx.bot.embed_colour,
                              timestamp=datetime.datetime.now())
        if option in ["fetch", "fetchrow", "fetchval"] and data:  # fetch query; place the results in a table
            keys = data[0].keys()
            table = utils.PrettyTable.default(keys)
            for entry in data:
                table.add_row(entry.values())
            embed.description = f"```\n{table.build_table(autoscale=True)}```"
        else:
            embed.description = f"```\n{data or 'Nothing was returned.'}```"

        await ctx.send(embed=embed)

    @admin.command(aliases=["ss"])
    async def screenshot(self, ctx: CustomContext, url: str):
        """
        Screenshots a webpage.

        `url` - The url of the webpage.
        """
        async with ctx.typing():
            with utils.StopWatch() as sw:
                try:
                    await ctx.bot.loop.run_in_executor(None, driver.get, url)
                except InvalidArgumentException:
                    return await ctx.send("Invalid url provided (did you forget the `http://` or `https://`?).")
                except WebDriverException:
                    return await ctx.send("Couldn't screenshot that webpage.")
            b = io.BytesIO(driver.get_screenshot_as_png())
            file = discord.File(b, filename="screenshot.png")
            embed = discord.Embed(colour=ctx.bot.embed_colour, timestamp=datetime.datetime.now())
            embed.set_image(url="attachment://screenshot.png")
            embed.set_footer(text=f"Finished in {sw.elapsed:.3f} seconds")
            await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Admin())
