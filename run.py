#!/usr/bin/env python
import os
from flask import Flask, abort, request, jsonify, g, url_for
from flask.ext.httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import xmlrpclib
from xmlrpclib import Error
import sys

user = 'admin'
pwd = 'P@ssw0rd'
dbname = 'coop_dev'
server = 'localhost'
port = '8069'

# initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'

# extensions
auth = HTTPBasicAuth()

class Member():
    
    def __init__(self,partner):
        self.partner = partner
    
    def generate_auth_token(self, expiration=600):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.partner['id']})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token
        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
        args = [('id','=',data['id'])]            
        ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)  
        fields = []
        partner = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids[0], fields)                
        return Member(partner)



@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    member = Member.verify_auth_token(username_or_token)
    if not member:
        # try to authenticate with username/password
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
        args = [('email','=',username_or_token)]            
        ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)
        if not ids: 
            return False
        fields= []
        partner = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids[0], fields)
        member = Member(partner)
    g.member = member
    return True

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('email','=',username)]            
    ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)  
    if not ids:
        abort(400)
    fields = []
    partner = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids[0], fields)
    member = Member(partner)
    return jsonify({'username': member.partner['email']})
    
@app.route('/api/users/<int:id>')
def get_user(id):    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('id','=',id)]            
    ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)  
    if not ids:
        abort(400)
    fields = []
    partner = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids[0], fields)
    return jsonify({'username': partner['email']})


@app.route('/api/token')
@auth.login_required
def get_auth_token():
    token = g.member.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


@app.route('/api/v1/resource')
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.member.partner['email']})

@app.route('/api/v1/ddsavingtype')
@auth.login_required
def ddsavingtype():
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = []            
    ids = sock.execute(dbname, uid, pwd, 'coop.saving.type', 'search', args)  
    if not ids:
        abort(400)
    fields = ['name']
    saving_types = sock.execute(dbname, uid, pwd, 'coop.saving.type', 'read', ids, fields)
    return jsonify(success="true",message="", results=saving_types)

@app.route('/api/v1/ddloantype')
@auth.login_required
def ddloantype():
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = []            
    ids = sock.execute(dbname, uid, pwd, 'coop.loan.type', 'search', args)  
    if not ids:
        abort(400)
    fields = ['name']
    saving_types = sock.execute(dbname, uid, pwd, 'coop.loan.type', 'read', ids, fields)
    return jsonify(success="true",message="", results=saving_types)
    

@app.route('/api/v1/mysavings')
@auth.login_required
def mysavings():
    partner = g.member.partner
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('res_partner_id','=',partner['id']),('state','=','paid')]            
    ids = sock.execute(dbname, uid, pwd, 'coop.saving.transaction', 'search', args)  
    if not ids:
        abort(400)
    fields = ['trans_date','saving_type_id','amount']
    saving_types = sock.execute(dbname, uid, pwd, 'coop.saving.transaction', 'read', ids, fields)
    return jsonify(success="true",message="", results=saving_types)

@app.route('/api/v1/myaccount')
@auth.login_required
def myaccount():
    partner = g.member.partner
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('id','=',partner['id'])]            
    ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)  
    if not ids:
        abort(400)
    fields = []
    saving_types = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids, fields)
    return jsonify(success="true",message="", results=saving_types)

@app.route('/api/v1/myloans')
@auth.login_required
def myloans():
    partner = g.member.partner
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('res_partner_id','=',partner['id']),('mobile_sync','=', False)]            
    ids = sock.execute(dbname, uid, pwd, 'coop.loan.transaction', 'search', args)  
    if not ids:
        abort(400)
    fields = ['id','trans_date','installment','total_amount']
    loan_transactions = sock.execute(dbname, uid, pwd, 'coop.loan.transaction', 'read', ids, fields)
    return jsonify(success="true",message="", results=loan_transactions)


@app.route('/api/v1/myloans/sync/<int:id>')
@auth.login_required
def sync_myloans(id):    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    values = {}
    values.update({'state':'sync'})            
    ids = sock.execute(dbname, uid, pwd, 'coop.loan.transaction', 'write', [id], values)  
    if not ids:
        abort(400)
    return jsonify(success="true",message="", results=[])

@app.route('/api/v1/requestloan')
#@auth.login_required
def requestloan():
    loan_type_id = request.json.get('loan_type_id')
    loan_amount = request.json.get('loan_amount')
    down_payment_amount = request.json.get('down_payment_amount')
    installment = request.json.get('installment')        
    partner = g.member.partner
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')
    values = {}
    values.update({'res_partner_id': partner['id']})
    values.update({'loan_type_id': loan_type_id})                
    values.update({'loan_amount': loan_amount})
    values.update({'down_payment_amount': down_payment_amount})
    values.update({'installment': installment})    
    result = sock.execute(dbname, uid, pwd, 'coop.loan.transaction', 'create', values)
    if result: 
        return jsonify(success="true",message="", results=[])
    else:
        return jsonify(success="false",message="Request Loan Error", results=[])

@app.route('/api/v1/mynotifications')
def my_notifications():
    return '[{"id":1,"subject":"Subject 01","description":"Description 01"},{"id":2,"subject":"Subject 02","description":"Description 02"}]'

if __name__ == "__main__":
    app.run()