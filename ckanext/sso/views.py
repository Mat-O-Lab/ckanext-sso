# encoding: utf-8

import logging

import ckan.lib.helpers as h
import ckan.model as model
from ckan.plugins import toolkit as tk
from ckan.views.user import RequestResetView, set_repoze_user
from flask import Blueprint

import ckanext.sso.helpers as helpers
from ckanext.sso.ssoclient import SSOClient

g = tk.g

log = logging.getLogger(__name__)

blueprint = Blueprint("sso", __name__)


@blueprint.before_app_request
def before_app_request():
    bp, action = tk.get_endpoint()
    if bp == "user" and action == "login" and helpers.check_default_login():
        return tk.redirect_to(h.url_for("sso.sso"))


def _log_user_into_ckan(resp):
    """Log the user into different CKAN versions.
    CKAN 2.10 introduces flask-login and login_user method.
    CKAN 2.9.6 added a security change and identifies the user
    with the internal id plus a serial autoincrement (currently static).
    CKAN <= 2.9.5 identifies the user only using the internal id.
    """
    if tk.check_ckan_version(min_version="2.10"):
        from ckan.common import login_user

        login_user(g.user_obj)
        return

    if tk.check_ckan_version(min_version="2.9.6"):
        user_id = "{},1".format(g.user_obj.id)
    else:
        user_id = tk.g.user
    set_repoze_user(user_id, resp)

    log.info(
        "User {0}<{1}> logged in successfully".format(g.user_obj.name, g.user_obj.email)
    )


def sso():
    log.info("SSO Login")
    auth_url = None
    sso_client = SSOClient()
    try:
        auth_url = sso_client.get_authorize_url()
    except Exception as e:
        log.error("Error getting auth url: {}".format(e))
        return tk.abort(500, "Error getting auth url: {}".format(e))
    return tk.redirect_to(auth_url)


def dashboard():
    data = tk.request.args
    sso_client = SSOClient()
    token = sso_client.get_token(data["code"])
    userinfo = sso_client.get_user_info(token)
    log.info("SSO Login: {}".format(userinfo))
    if userinfo:
        pref_username = userinfo.get("preferred_username", "")
        if pref_username:
            user_name = helpers.ensure_unique_username(pref_username)
        else:
            user_name = helpers.ensure_unique_username(userinfo["name"])
        user_dict = {
            "name": user_name,
            "email": userinfo["email"],
            "password": helpers.generate_password(),
            "fullname": userinfo["name"],
            "plugin_extras": {"idp": userinfo["sub"]},
        }
        context = {"model": model, "session": model.Session}
        g.user_obj = helpers.process_user(user_dict)
        g.user = g.user_obj.name
        context["user"] = g.user
        context["auth_user_obj"] = g.user_obj

        response = tk.redirect_to(tk.url_for("user.me", context))

        _log_user_into_ckan(response)
        log.info("Logged in success")
        return response
    else:
        return tk.redirect_to(tk.url_for("user.login"))


def reset_password():
    email = tk.request.form.get("user", None)
    if "@" not in email:
        log.info(f"User requested reset link for invalid email: {email}")
        h.flash_error("Invalid email address")
        return tk.redirect_to(tk.url_for("user.request_reset"))
    user = model.User.by_email(email)
    if not user:
        log.info("User requested reset link for unknown user: {}".format(email))
        return tk.redirect_to(tk.url_for("user.login"))
    user_extras = user[0].plugin_extras
    if user_extras and user_extras.get("idp", None) == "google":
        log.info("User requested reset link for google user: {}".format(email))
        h.flash_error("Invalid email address")
        return tk.redirect_to(tk.url_for("user.login"))
    return RequestResetView().post()


blueprint.add_url_rule("/sso", view_func=sso)
blueprint.add_url_rule("/dashboard", view_func=dashboard)
blueprint.add_url_rule("/reset_password", view_func=reset_password, methods=["POST"])


def get_blueprint():
    return blueprint
