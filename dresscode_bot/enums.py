from enum import Enum


class ChatPermissionEnum(str, Enum):
    SEND_MESSAGES = "can_send_messages"
    SEND_AUDIOS = "can_send_audios"
    SEND_DOCUMENTS = "can_send_documents"
    SEND_PHOTOS = "can_send_photos"
    SEND_VIDEOS = "can_send_videos"
    SEND_VIDEO_NOTES = "can_send_video_notes"
    SEND_POLLS = "can_send_polls"
    SEND_OTHER_MESSAGES = "can_send_other_messages"
    ADD_WEB_PAGE_PREVIEWS = "can_add_web_page_previews"
    CHANGE_INFO = "can_change_info"
    INVITE_USERS = "can_invite_users"
    PIN_MESSAGES = "can_pin_messages"
    MANAGE_TOPICS = "can_manage_topics"


class BotMethodEnum(str, Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"
