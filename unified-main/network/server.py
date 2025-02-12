from flask import Flask, request, jsonify
import logging
from threading import Event

app = Flask(__name__)
