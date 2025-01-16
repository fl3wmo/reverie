import asyncio
import typing

import discord

import templates

if typing.TYPE_CHECKING:
    from database import Database


async def _get_webhook(channel: discord.TextChannel) -> discord.Webhook:
    """Retrieve an existing webhook or create a new one."""
    webhooks = await channel.webhooks()
    if webhooks:
        return webhooks[0]
    return await channel.create_webhook(name="Saved messages")


async def _copy_message(message: discord.Message, target_message: discord.Message) -> dict:
    """Prepare the content and files from a message for sending via webhook."""
    files = [await attachment.to_file() for attachment in message.attachments]
    return {
        "target": message.id == target_message.id,
        "content": message.content,
        "files": files,
        "username": ('📸 ' if message.id == target_message.id else '') + message.author.display_name,
        "avatar_url": message.author.display_avatar.url,
        "allowed_mentions": discord.AllowedMentions.none(),
        "embeds": message.embeds,
    }


async def _update_embed(message: discord.Message, thread: discord.Thread, sent_message: discord.Message):
    """Update the message embed with a link to the saved screenshot."""
    embed = message.embeds[0]
    last_field = embed.fields[-1]

    # Update last field
    embed.set_field_at(-1, name=last_field.name, value=last_field.value, inline=True)

    # Add new field with link to the copied message
    embed.add_field(
        name="📸 Сообщение",
        value=f'[{sent_message.content or "Сообщение"}]({thread.jump_url}/{sent_message.id})',
        inline=True,
    )

    await message.edit(embed=embed)


async def _process_messages(
        webhook: discord.Webhook,
        messages: list[discord.Message],
        target_message: discord.Message,
        thread: discord.Thread
):
    """Send copied messages to the thread via the webhook."""
    copied_messages = await asyncio.gather(*[_copy_message(msg, target_message) for msg in messages])
    screenshot_target = None

    for copied_msg in copied_messages:
        target = copied_msg.pop("target")
        sent_message = await webhook.send(**copied_msg, thread=thread, wait=target)
        if target:
            screenshot_target = sent_message
    return screenshot_target


async def screenshot_messages(
        message: discord.Message,
        target_message: discord.Message,
        messages: list[discord.Message],
        action_id: int = None,
        db: 'Database' = None
):
    """Main function to handle the screenshot process."""
    channel = message.channel
    webhook = await _get_webhook(channel)
    thread = await message.create_thread(name="📸 Скриншот сообщений")

    sent_message = await _process_messages(webhook, messages, target_message, thread)

    if sent_message:
        await _update_embed(message, thread, sent_message)
        await db.actions.set_prove_link(action_id, f"{thread.jump_url}/{sent_message.id}")

    await target_message.delete()
    await thread.edit(archived=True)


class Pagination(discord.ui.View):
    def __init__(self, bot, interaction, owner, data, page_size=5, embed_title="Page"):
        super().__init__()
        self.bot = bot
        self.interaction = interaction
        self.owner = owner
        self.data = data
        self.page_size = page_size
        self.pages = self._paginate_data(data)
        self.current_page = 0
        self.embed_title = embed_title

        self._update_buttons()

    def _paginate_data(self, data):
        """Split data into pages of size `page_size`."""
        return [data[i:i + self.page_size] for i in range(0, len(data), self.page_size)]

    async def send_initial_message(self):
        """Send the initial paginated message with view."""
        embed = self._create_embed(self.current_page)
        await self.interaction.response.send_message(templates.embed_mentions(embed), embed=embed, view=self, ephemeral=True)

    def _create_embed(self, page_number):
        """Create an embed for the given page number."""
        page_data = self.pages[page_number]
        description = "\n".join([item[1].to_text(item[0]) for index, item in enumerate(page_data)])
        embed = discord.Embed(title=self.embed_title,
                              description=description, color=discord.Color.dark_red())
        embed.set_footer(text=f'Страница {page_number + 1}/{len(self.pages)}')
        return embed

    async def _update_message(self):
        """Update the message with the current page's embed and the pagination view."""
        embed = self._create_embed(self.current_page)
        self._update_buttons()
        await self.interaction.edit_original_response(content=templates.embed_mentions(embed), embed=embed, view=self)

    def _update_buttons(self):
        """Update button states based on the current page."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(emoji='⬅️', style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message('Вам нельзя использовать эту кнопку.', ephemeral=True)

        if self.current_page > 0:
            self.current_page -= 1
            await self._update_message()
            await interaction.response.defer(ephemeral=True)

    @discord.ui.button(emoji='➡️', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message('Вам нельзя использовать эту кнопку.', ephemeral=True)

        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self._update_message()
            await interaction.response.defer(ephemeral=True)


def find_channel_by_name(guild: discord.Guild, *names: str) -> discord.TextChannel:
    return [c for c in guild.text_channels if any(name in c.name for name in names)][0]
