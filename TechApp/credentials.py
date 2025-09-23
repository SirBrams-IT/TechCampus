import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MpesaAccessToken:
    @staticmethod
    def get_access_token():
        try:
            consumer_key = settings.MPESA_CONSUMER_KEY
            consumer_secret = settings.MPESA_CONSUMER_SECRET
            
            if not consumer_key or not consumer_secret:
                logger.error("❌ M-Pesa credentials are missing or empty")
                return None
            
            api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
            
            logger.info(f"🔑 Requesting access token with key: {consumer_key[:10]}...")
            
            response = requests.get(
                api_url,
                auth=HTTPBasicAuth(consumer_key, consumer_secret),
                timeout=30
            )
            
            logger.info(f"🔑 Access token response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                if access_token:
                    logger.info("✅ Access token obtained successfully")
                    return access_token
                else:
                    logger.error("❌ No access token in response")
                    return None
            else:
                logger.error(f"❌ Failed to get access token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception getting access token: {str(e)}")
            return None

class LipanaMpesaPpassword:
    @staticmethod
    def get_password():
        try:
            business_shortcode = settings.MPESA_BUSINESS_SHORTCODE
            passkey = settings.MPESA_PASSKEY
            lipa_time = datetime.now().strftime('%Y%m%d%H%M%S')
            
            data_to_encode = business_shortcode + passkey + lipa_time
            online_password = base64.b64encode(data_to_encode.encode())
            
            logger.info(f"🔐 Password generated for shortcode: {business_shortcode}")
            
            return {
                'password': online_password.decode('utf-8'),
                'timestamp': lipa_time,
                'business_shortcode': business_shortcode
            }
        except Exception as e:
            logger.error(f"❌ Error generating password: {str(e)}")
            return None