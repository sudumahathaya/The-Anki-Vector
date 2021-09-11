import time
import logging
from Config import Config
from pyrogram import Client, filters
from sql_helpers import forceSubscribe_sql as sql
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

logging.basicConfig(level=logging.INFO)

static_data_filter = filters.create(lambda _, __, query: query.data == "onUnMuteRequest")
@Client.on_callback_query(static_data_filter)
def _onUnMuteRequest(client, cb):
  user_id = cb.from_user.id
  chat_id = cb.message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    channel = chat_db.channel
    chat_member = client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
      if chat_member.restricted_by.id == (client.get_me()).id:
          try:
            client.get_chat_member(channel, user_id)
            client.unban_chat_member(chat_id, user_id)
            if cb.message.reply_to_message.from_user.id == user_id:
              cb.message.delete()
          except UserNotParticipant:
            client.answer_callback_query(cb.id, text="❗ චැනල් එකට Join වෙලා Unmute Button එක ඔබන්න...", show_alert=True)
      else:
        client.answer_callback_query(cb.id, text="❗ ඇඩ්මින්ලා ඔයාව වෙන හේතුවක් නිසා Mute කරලා.", show_alert=True)
    else:
      if not client.get_chat_member(chat_id, (client.get_me()).id).status == 'administrator':
        client.send_message(chat_id, f"❗ **{cb.from_user.mention}  උත්සාහ කරනවා ඔබව Unmute කරන්න. නමුත් මම සමූහයේ ඇඩ්මින්වරයකු නොවන නිසා එය සිදුකිරීමට නොහැක. ඇඩ්මින් තනතුර ලබා දී නැවත උත්සාහ කරන්න....**\n__#Leaving this chat...__")
        client.leave_chat(chat_id)
      else:
        client.answer_callback_query(cb.id, text="❗ අවවාදයයි: ඔබට කතාකිරීමේ හැකියාව තිබියදී Unmute Button එක ඔබන්න එපා.", show_alert=True)



@Client.on_message(filters.text & ~filters.private & ~filters.edited, group=1)
def _check_member(client, message):
  chat_id = message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    user_id = message.from_user.id
    if not client.get_chat_member(chat_id, user_id).status in ("administrator", "creator") and not user_id in Config.SUDO_USERS:
      channel = chat_db.channel
      if channel.startswith("-"):
          channel_url = client.export_chat_invite_link(int(channel))
      else:
          channel_url = f"https://t.me/{channel}"
      try:
        client.get_chat_member(channel, user_id)
      except UserNotParticipant:
        try:
          sent_message = message.reply_text(
              " {} , ඔබ අපගේ චැනල් එක Subscribe කරලා නැහැ. කරුණාකර චැනල් එකට Join වී Unmute Button එක ඔබන්න.".format(message.from_user.mention, channel, channel),
              disable_web_page_preview=True,
             reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Subscribe My Channel", url=channel_url)
                ],
                [
                    InlineKeyboardButton("UnMute Me", callback_data="onUnMuteRequest")
                ]
            ]
        )
          )
          client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        except ChatAdminRequired:
          sent_message.edit("❗ **මම මෙහි ඇඩ්මින්වරයකු නොවෙයි.**\n__මට Ban Permission සමග ඇඩ්මින් ලබා දී නැවත උත්සාහ කරන්න.\n#Leaving this chat...__")
          client.leave_chat(chat_id)
      except ChatAdminRequired:
        client.send_message(chat_id, text=f"❗ **මම ඇඩ්මින්වරයකු නොවෙයි [channel]({channel_url}) මෙම චැනලයේ...**\n__මට ඇඩ්මින් ලබා දී නැවත උත්සාහ කරන්න.\n#Leaving this chat...__")
        client.leave_chat(chat_id)


@Client.on_message(filters.command(["forcesubscribe", "fsub", "fsub@ForceSubscriber_UBot", "forcesubscribe@ForceSubscriber_UBot"]) & ~filters.private)
def config(client, message):
  user = client.get_chat_member(message.chat.id, message.from_user.id)
  if user.status == "creator" or user.user.id in Config.SUDO_USERS:
    chat_id = message.chat.id
    if len(message.command) > 1:
      input_str = message.command[1]
      input_str = input_str.replace("@", "")
      if input_str.lower() in ("off", "no", "disable"):
        sql.disapprove(chat_id)
        message.reply_text("❌ **Force Subscribe is Disabled Successfully.**")
      elif input_str.lower() in ('clear'):
        sent_message = message.reply_text('**Unmuting all members who are muted by me...**')
        try:
          for chat_member in client.get_chat_members(message.chat.id, filter="restricted"):
            if chat_member.restricted_by.id == (client.get_me()).id:
                client.unban_chat_member(chat_id, chat_member.user.id)
                time.sleep(1)
          sent_message.edit('✅ **මම Mute කළ සියලු දෙනා Unmute කරන ලදී.**')
        except ChatAdminRequired:
          sent_message.edit('❗ **මම මෙහි ඇඩ්මින්වරයකු නොවේ...**\n__මට Unmute කරන්න බැහැ මාව Ban Permission සමග ඇඩ්මින් තනතුරට පත් කරන්න.__')
      else:
        try:
          client.get_chat_member(input_str, "me")
          sql.add_channel(chat_id, input_str)
          if input_str.startswith("-"):
              channel_url = client.export_chat_invite_link(int(input_str))
          else:
              channel_url = f"https://t.me/{input_str}"
          message.reply_text(f"✅ **Force Subscribe is Enabled**\n__Force Subscribe is enabled, all the group members have to subscribe this [channel]({channel_url}) in order to send messages in this group.__", disable_web_page_preview=True)
        except UserNotParticipant:
          message.reply_text(f"❗ **මම චැනලයේ ඇඩ්මින්වරයකු නොවේ.**\n__මම මෙහි ඇඩ්මින්වරයකු නොවේ[channel]({channel_url}). ඈඩ්මින් තනතුර ලබා දී නැවත උත්සාහ කරන්න.__", disable_web_page_preview=True)
        except (UsernameNotOccupied, PeerIdInvalid):
          message.reply_text(f"❗ **Invalid Channel Username/ID.**")
        except Exception as err:
          message.reply_text(f"❗ **ERROR:** ```{err}```")
    else:
      if sql.fs_settings(chat_id):
        my_channel = sql.fs_settings(chat_id).channel
        if my_channel.startswith("-"):
            channel_url = client.export_chat_invite_link(int(input_str))
        else:
            channel_url = f"https://t.me/{my_channel}"
        message.reply_text(f"✅ **Force Subscribe is enabled in this chat.**\n__For this [Channel]({channel_url})__", disable_web_page_preview=True)
      else:
        message.reply_text("❌ **Force Subscribe is disabled in this chat.**")
  else:
      message.reply_text("❗ **Group Creator Required**\n__You have to be the group creator to do that.__")


__help__ = """
*ForceSubscribe:*

❂ Anki Vector can mute members who are not subscribed your channel until they subscribe
❂ When enabled I will mute unsubscribed members and show them a unmute button. When they pressed the button I will unmute them

*Setup*
1) First of all add me in the group as admin with ban users permission and in the channel as admin.
Note: Only creator of the group can setup me and i will not allow force subscribe again if not done so.
 
*Commmands*
❂ /ForceSubscribe - To get the current settings.
❂ /ForceSubscribe no/off/disable - To turn of ForceSubscribe.
❂ /ForceSubscribe {channel username} - To turn on and setup the channel.
❂ /ForceSubscribe clear - To unmute all members who muted by me.

Note: /FSub is an alias of /ForceSubscribe

 
"""
__mod_name__ = "Force Subscribe"
