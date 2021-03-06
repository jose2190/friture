#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Timothée Lecomte

# This file is part of Friture.
#
# Friture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# Friture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Friture.  If not, see <http://www.gnu.org/licenses/>.

import numpy
from PyQt4 import Qt, QtCore, QtGui
import PyQt4.Qwt5 as Qwt
from friture.audiobackend import SAMPLING_RATE

from friture.lookup_table import pyx_color_from_float_2D

class CanvasScaledSpectrogram(QtCore.QObject):
	def __init__(self, logger, canvas_height = 2,  canvas_width = 2):
		QtCore.QObject.__init__(self)

		# store the logger instance
		self.logger = logger

		self.canvas_height = canvas_height
		self.canvas_width = canvas_width

		#self.fullspectrogram = numpy.zeros((self.canvas_height, self.time_bin_number(), 4), dtype = numpy.uint8)
		self.pixmap = QtGui.QPixmap(2*self.canvas_width,  self.canvas_height)
		#print "pixmap info : hasAlpha =", self.pixmap.hasAlpha(), ", depth =", self.pixmap.depth(), ", default depth =", self.pixmap.defaultDepth()
		self.pixmap.fill(QtGui.QColor("black"))
		self.painter = QtGui.QPainter()
		self.offset = 0
		# prepare a custom colormap black->blue->green->yellow->red->white
		self.colorMap = Qwt.QwtLinearColorMap(Qt.Qt.black, Qt.Qt.white)
		self.colorMap.addColorStop(0.2, Qt.Qt.blue)
		self.colorMap.addColorStop(0.4, Qt.Qt.green)
		self.colorMap.addColorStop(0.6, Qt.Qt.yellow)
		self.colorMap.addColorStop(0.8, Qt.Qt.red)
		self.prepare_palette()
		# performance timer
		self.time = QtCore.QTime()
		self.time.start()
		#self.logfile = open("latency_log.txt",'w')

	def erase(self):
		#self.fullspectrogram = numpy.zeros((self.canvas_height, self.time_bin_number(), 4), dtype = numpy.uint8)
		self.pixmap = QtGui.QPixmap(2*self.canvas_width,  self.canvas_height)
		self.pixmap.fill(QtGui.QColor("black"))
		self.offset = 0

	def setcanvas_height(self, canvas_height):
		if self.canvas_height <> canvas_height:
			self.canvas_height = canvas_height
			self.erase()
			self.logger.push("Spectrogram image: canvas_height changed, now: %d" %(canvas_height))

	def setcanvas_width(self, canvas_width):
		if self.canvas_width <> canvas_width:
			self.canvas_width = canvas_width
			self.erase()
			self.emit(QtCore.SIGNAL("canvasWidthChanged"), canvas_width)
			self.logger.push("Spectrogram image: canvas_width changed, now: %d" %(canvas_width))

	def addData(self, xyzs):
		# revert the frequency axis so that the larger frequencies
		# are at the top of the widget
		xyzs = xyzs[::-1, :]

		width = xyzs.shape[1]
  
		# convert the data to colors, and then to a data string 
		# that QImage can understand
		byteString = self.floats_to_bytes(xyzs)

		myimage = self.prepare_image(byteString, width, xyzs.shape[0])

		# Now, draw the image onto the widget pixmap, which has
		# the structure of a 2D ringbuffer

		# first copy, always complete
		source1 = QtCore.QRectF(0, 0, width, xyzs.shape[0])
		target1 = QtCore.QRectF(self.offset, 0, width, xyzs.shape[0])
		# second copy, can be folded
		direct = min(width, self.canvas_width - self.offset)
		folded = width - direct
		source2a = QtCore.QRectF(0, 0, direct, xyzs.shape[0])
		target2a = QtCore.QRectF(self.offset + self.canvas_width, 0, direct, xyzs.shape[0])
		source2b = QtCore.QRectF(direct, 0, folded, xyzs.shape[0])
		target2b = QtCore.QRectF(0, 0, folded, xyzs.shape[0])

		self.painter.begin(self.pixmap)
		self.painter.drawImage(target1, myimage, source1)
		self.painter.drawImage(target2a, myimage, source2a)
		self.painter.drawImage(target2b, myimage, source2b)
		self.painter.end()

		#updating the offset
		self.offset = (self.offset + xyzs.shape[1]) % self.canvas_width

	def floats_to_bytes(self, data):
		#dat1 = (255. * data).astype(numpy.uint8)
		#dat4 = dat1.repeat(4)
		dat4 = self.color_from_float(data)
		return dat4.tostring()

	# defined as a separate function so that it appears in the profiler
	# NOTE: QImage with a colormap is slower (by a factor of 2) than the custom
	# colormap code here.
	def prepare_image(self, byteString, width, height):
		myimage = QtGui.QImage(byteString, width, height, QtGui.QImage.Format_RGB32)
		return myimage

	def prepare_palette(self):
		self.colors = numpy.zeros((256), dtype=numpy.uint32)
		for i in range(256):
			self.colors[i] = self.colorMap.rgb(Qwt.QwtDoubleInterval(0,255), i)

	def color_from_float(self, v):
		return pyx_color_from_float_2D(self.colors, v)
		#d = (v*255).astype(numpy.uint8)
		#return self.colors[d]

	#def interpolate_colors(colors, flat=False, num_colors=256):
		#colors =
		#""" given a list of colors, create a larger list of colors interpolating
		#the first one. If flatten is True a list of numers will be returned. If
		#False, a list of (r,g,b) tuples. num_colors is the number of colors wanted
		#in the final list """

		#palette = []

		#for i in range(num_colors):
			#index = (i * (len(colors) - 1))/(num_colors - 1.0)
			#index_int = int(index)
			#alpha = index - float(index_int)

			#if alpha > 0:
			#r = (1.0 - alpha) * colors[index_int][0] + alpha * colors[index_int + 1][0]
			#g = (1.0 - alpha) * colors[index_int][1] + alpha * colors[index_int + 1][1]
			#b = (1.0 - alpha) * colors[index_int][2] + alpha * colors[index_int + 1][2]
			#else:
			#r = (1.0 - alpha) * colors[index_int][0]
			#g = (1.0 - alpha) * colors[index_int][1]
			#b = (1.0 - alpha) * colors[index_int][2]

			#if flat:
			#palette.extend((int(r), int(g), int(b)))
			#else:
			#palette.append((int(r), int(g), int(b)))

		#return palette

	def getpixmap(self):
		return self.pixmap

	def getpixmapoffset(self):
		return self.offset

# plan :
# 1. quickly convert each piece of data to a pixmap, with the right pixel size
# as QImage to QPixmap conversion is slow, and scaling is slow too
# 2. use a cache of size M=2*N
# 3. write in the cache at the position j and j+N
# 4. the data part that is to be drawn can be read contiguously from j+1 to j+1+N
