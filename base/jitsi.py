from django.conf import settings
import uuid

class JitsiMeetManager:
    @staticmethod
    def generate_meeting_credentials():
        """Generate unique meeting credentials for Jitsi Meet"""
        try:
            room_id = str(uuid.uuid4())[:8]
            room_name = f"{settings.JITSI_MEET['ROOM_NAME_PREFIX']}{room_id}"
            
            meeting_link = f"https://{settings.JITSI_MEET['DOMAIN']}/{room_name}"
            meeting_id = room_name
            meeting_password = str(uuid.uuid4())[:6].upper()
            
            print(f"Generated meeting link: {meeting_link}")
            print(f"Generated meeting ID: {meeting_id}")
            print(f"Generated meeting password: {meeting_password}")
            
            return {
                'meeting_link': meeting_link,
                'meeting_id': meeting_id,
                'meeting_password': meeting_password
            }
        except Exception as e:
            print(f"Error in generate_meeting_credentials: {str(e)}")
            raise