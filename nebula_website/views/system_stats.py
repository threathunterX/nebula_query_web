# -*- coding: utf-8 -*-

'''
nginx 已经将这个请求转发到java-web

'''

# import logging
# from flask import Blueprint, jsonify
#
# from nebula_website import data_client
#
#
# mod = Blueprint("system_stats", __name__)
#
#
# @mod.route('/system/license', methods=["GET"])
# def LicenseInfoHandler():
#     """
#     获取nebula证书信息
#
#     @API
#     summary: 获取nebula证书信息(new)
#     description: nebula证书信息(new)
#     tags:
#       - system
#     responses:
#       '200':
#         description: 返回一个对象
#         schema:
#           $ref: '#/definitions/Version'
#       default:
#         description: Unexcepted error
#         schema:
#           $ref: '#/definitions/Error'
#     """
#
#     license = data_client.get_license_info()
#     if license:
#         return jsonify(license)
#     else:
#         return jsonify(status=500, msg='fail to get license config')
