# encoding: utf-8

import logging

from requests_oauthlib import OAuth2Session
from ckan.plugins import toolkit as tk

log = logging.getLogger(__name__)


class SSOClient(object):
    def __init__(self):
        self.authorize_url = tk.config.get('ckanext.sso.authorization_endpoint')
        self.client_id = tk.config.get('ckanext.sso.client_id')
        self.redirect_url = tk.config.get('ckanext.sso.redirect_url')
        self.client_secret = tk.config.get('ckanext.sso.client_secret')
        response_type = tk.config.get('ckanext.sso.response_type')
        self.scope = tk.config.get('ckanext.sso.scope')
        self.token_url = tk.config.get('ckanext.sso.access_token_url')
        self.user_info_url = tk.config.get('ckanext.sso.user_info')

    def get_authorize_url(self):
        log.debug('get_authorize_url')
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_url,
                              scope=self.scope)
        authorization_url, state = oauth.authorization_url(self.authorize_url)
        return authorization_url

    def get_token(self, code):
        log.debug('get_token')
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_url,
                              scope=self.scope)
        token = oauth.fetch_token(self.token_url, code=code,
                                  client_secret=self.client_secret)
        return token

    def get_user_info(self, token):
        log.debug('get_user_info')
        oauth = OAuth2Session(self.client_id, token=token)
        user_info = oauth.get(self.user_info_url)
        return user_info.json()
