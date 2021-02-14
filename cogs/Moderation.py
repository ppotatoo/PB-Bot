import discord

from discord.ext import commands

from utils.classes import CustomContext


class Moderation(commands.Cog):
    """
    Moderation commands.
    """
    def cog_check(self, ctx: CustomContext):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.command()
    async def kick(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """
        Kicks a member from the server.

        `member` - The member to kick.
        `reason` - The reason why the member was kicked. Defaults to "No reason provided.".
        """
        if ctx.author.top_role <= member.top_role:
            return await ctx.send("You can't kick this member as they are higher or equal to you in the role hierarchy.")
        reason = reason or "No reason provided."
        await member.send(f"You have been kicked from **`{ctx.guild}`** by `{ctx.author}`.\n**Reason:** {reason}")
        await member.kick(reason=f"kick done by {ctx.author}; reason: {reason}")
        await ctx.send("👌")

    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.command()
    async def ban(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """
        Bans a member from the server.

        `member` - The member to ban.
        `reason` - The reason why the member was banned. Defaults to "No reason provided.".
        """
        if ctx.author.top_role <= member.top_role:
            return await ctx.send("You can't ban this member as they are higher or equal to you in the role hierarchy.")
        reason = reason or "No reason provided."
        await member.send(f"You have been banned from **`{ctx.guild}`** by `{ctx.author}`.\n**Reason:** {reason}")
        await member.ban(reason=f"ban done by {ctx.author}; reason: {reason}")
        await ctx.send("👌")


def setup(bot):
    bot.add_cog(Moderation())
