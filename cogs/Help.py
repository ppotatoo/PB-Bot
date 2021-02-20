import discord
import difflib

from discord.ext import commands
from contextlib import suppress

from utils import utils
from utils.classes import CustomContext

# constants

command_attrs = {"aliases": ["h"]}


class CustomHelpCommand(commands.HelpCommand):
    """
    Custom help command.
    """
    context: CustomContext

    async def send_bot_help(self, _):
        data = {0: None}
        cogs = [cog_pair for cog_pair in self.context.bot.cogs.items() if cog_pair[1].get_commands()]
        data.update({num: cog_pair for num, cog_pair in enumerate(cogs, start=1)})
        pages = utils.PaginatedHelpCommand(source=utils.HelpSource(data), clear_reactions_after=True)
        await pages.start(self.context)
        with suppress(discord.HTTPException):
            await self.context.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(title=f"Help on Command `{command.name}`",
                              description=command.help or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Signature:", value=f"{command.name} {command.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{command.cog_name}", inline=False)

        try:
            can_run = await command.can_run(self.context)
            if can_run:
                can_run = self.context.bot.emoji_dict["green_tick"]
            else:
                can_run = self.context.bot.emoji_dict["red_tick"]
        except commands.CommandError:
            can_run = self.context.bot.emoji_dict["red_tick"]

        embed.add_field(name="Can Use:", value=can_run)
        embed.add_field(name="Aliases:", value="\n".join(command.aliases) or "None", inline=False)
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)

        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        embed = discord.Embed(title=f"Help on Category `{cog.qualified_name}`",
                              description=cog.description or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Commands in this Category:",
                        value="\n".join(str(command) for command in cog.get_commands()) or "None")
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)

        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        embed = discord.Embed(title=f"Help on Command Group `{group.name}`",
                              description=group.help or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Signature:", value=f"{group.name} {group.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{group.cog_name}", inline=False)

        try:
            can_run = await group.can_run(self.context)
            if can_run:
                can_run = self.context.bot.emoji_dict["green_tick"]
            else:
                can_run = self.context.bot.emoji_dict["red_tick"]
        except commands.CommandError:
            can_run = self.context.bot.emoji_dict["red_tick"]

        embed.add_field(name="Can Use:", value=can_run)
        embed.add_field(name="Aliases:", value="\n".join(group.aliases) or "None", inline=False)
        embed.add_field(name="Commands in this Group:",
                        value="\n".join(str(command) for command in group.walk_commands()) or "None")
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)

        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def command_not_found(self, string: str):
        matches = difflib.get_close_matches(string, self.context.bot.command_list)
        if not matches:
            return f"Command '{string}' is not found."
        top3 = "\n".join(matches[:3])
        return f"Command '{string}' is not found. Did you mean:\n{top3}"


def setup(bot):
    bot.help_command = CustomHelpCommand(command_attrs=command_attrs)


def teardown(bot):
    bot.help_command = None
