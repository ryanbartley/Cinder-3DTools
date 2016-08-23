
import Base
reload( Base )
from Base import BaseMaterial
from Base import BaseMesh
from Base import BaseLight
from Base import BaseCamera
from Base import BaseNode

import GltfWriter
reload( GltfWriter )
from GltfWriter import GltfWriter

import TriMesh
reload( TriMesh )
from TriMesh import TriMesh

import c4d
import array
import math

class _c4d( object ):
	OBJECT_BASE_MESH	= 5100
	OBJECT_CONE     	= 5162
	OBJECT_CUBE     	= 5159
	OBJECT_CYLINDER 	= 5170
	OBJECT_DISC     	= 5164
	OBJECT_PLANE    	= 5168
	OBJECT_POLYGON  	= 5174
	OBJECT_SPHERE   	= 5160
	OBJECT_TORUS    	= 5163
	OBJECT_CAPSULE  	= 5171
	OBJECT_OIL_TANK 	= 5172
	OBJECT_TUBE     	= 5165
	OBJECT_PYRAMID  	= 5167
	OBJECT_PLATONIC 	= 5161
	OBJECT_CAMERA 		= 5103
	OBJECT_LIGHT		= 5102
	OBJECT_NULL			= 5140

	UNIT_SCALE 			= 0.01
	pass

meshObjects = [
			_c4d.OBJECT_CONE,
			_c4d.OBJECT_CUBE,
			_c4d.OBJECT_CYLINDER,
			_c4d.OBJECT_DISC,
			_c4d.OBJECT_PLANE,
			_c4d.OBJECT_POLYGON,
			_c4d.OBJECT_SPHERE,
			_c4d.OBJECT_TORUS,
			_c4d.OBJECT_CAPSULE,
			_c4d.OBJECT_OIL_TANK,
			_c4d.OBJECT_TUBE,
			_c4d.OBJECT_PYRAMID,
			_c4d.OBJECT_PLATONIC
		]

def convertC4DMatrix( c4dMatrix ):
	elements = []
	elements.append( c4dMatrix.v1.x )
	elements.append( c4dMatrix.v1.y )
	elements.append( c4dMatrix.v1.z )
	elements.append( 0.0 )
	elements.append( c4dMatrix.v2.x )
	elements.append( c4dMatrix.v2.y )
	elements.append( c4dMatrix.v2.z )
	elements.append( 0.0 )
	elements.append( c4dMatrix.v3.x )
	elements.append( c4dMatrix.v3.y )
	elements.append( c4dMatrix.v3.z )
	elements.append( 0.0 )
	elements.append( c4dMatrix.off.x * _c4d.UNIT_SCALE )
	elements.append( c4dMatrix.off.y * _c4d.UNIT_SCALE )
	elements.append( c4dMatrix.off.z * _c4d.UNIT_SCALE )
	elements.append( 1.0 )
	return elements
	pass

def convertColor( colorVec ):
	return [colorVec.x, colorVec.y, colorVec.z, 1.0]

## \class C4DMaterial
#
#
class C4DMaterial( BaseMaterial ):
	## c'tor
	MATERIAL_VALS = [
		(c4d.MATERIAL_USE_TRANSPARENCY, None, 							c4d.MATERIAL_TRANSPARENCY_COLOR, "transparency"),
		(c4d.MATERIAL_USE_COLOR, 		c4d.MATERIAL_COLOR_SHADER, 		c4d.MATERIAL_COLOR_COLOR, "color"),
		(c4d.MATERIAL_USE_NORMAL, 		c4d.MATERIAL_NORMAL_SHADER, 	None, "normal" ),
		(c4d.MATERIAL_USE_DIFFUSION, 	c4d.MATERIAL_DIFFUSION_SHADER, 	None, "diffuse"),
		(c4d.MATERIAL_USE_SPECULARCOLOR,c4d.MATERIAL_SPECULAR_SHADER, 	c4d.MATERIAL_SPECULAR_COLOR, "specular")
	]

	def __init__( self, materialSet ):
		#print( "C4DMaterial c'tor" )
		BaseMaterial.__init__(self)
		#print "should've called base con"
		self.material = materialSet["material"]
		self.name = self.material.GetName()
		#GL_REPEAT: The integer part of the coordinate will be ignored and a repeating pattern is formed.
		#GL_MIRRORED_REPEAT: The texture will also be repeated, but it will be mirrored when the integer part of the coordinate is odd.
		#GL_CLAMP_TO_EDGE: The coordinate will simply be clamped between 0 and 1.
		#GL_CLAMP_TO_BORDER: The coordinates that fall outside the range will be given a specified border color.
		# TODO: decide what the different values determine
		if materialSet["repeat_u"] == 1.0:
			self.wraps.append( GltfWriter.CLAMP_TO_EDGE )
		else:
			self.wraps.append( GltfWriter.REPEAT )
		if materialSet["repeat_v"] == 1.0:
			self.wraps.append( GltfWriter.CLAMP_TO_EDGE )
		else:
			self.wraps.append( GltfWriter.REPEAT )
		
		# TODO: decide what to do with these.	
		# c4d.MATERIAL_USE_FOG c4d.MATERIAL_USE_SPECULAR c4d.MATERIAL_USE_GLOW
		
		for use, texture, color, key in C4DMaterial.MATERIAL_VALS:
			self.cacheMaterialValues( use, texture, color, key )

		# TODO: How do we find these values
		self.colors["ambient"] = [0.2, 0.2, 0.2, 1.0]
		self.colors["emission"] = [0, 0, 0, 1.0]
		self.colors["shininess"] = 256.0
		pass

	def cacheMaterialValues( self, use, texture, color, key ):
		if self.material[use]==True:         
			if self.material[texture]:
				if self.material[texture].GetType() == c4d.Xbitmap:
					self.files[key] = str(self.material[texture][c4d.BITMAPSHADER_FILENAME])
				else:
					print "only supported shaders are bitmapshader!"
			elif self.material[color]:
				self.colors[key] = convertColor(self.material[color]) 
		pass

## \class BaseMesh
#
#
class C4DMesh( BaseMesh ):
	## c'tor
	def __init__( self, meshObj ):
		#print( "BaseMesh c'tor" )
		BaseMesh.__init__( self )
		# name is whatever
		self.meshObj = meshObj
		self.name = meshObj.GetName()
		# key has to be unique, which this probably won't
		# first we get the division of faces
		materialSets = self.getMaterialSets()
		for materialSet in materialSets: 
			# Cache the material first
			mat = C4DMaterial( materialSet )
			# Cache the buffers
			trimesh = self.createTriMesh( self.meshObj, materialSet["faces"] )
			# push it on to the primitives
			self.primitives.append( { "trimesh" : trimesh, "material" : mat } )		
			pass
		pass

	def getMaterialSets( self ):
		materialSets = []
		# Get tags
		tags = self.meshObj.GetTags()
		# Find the necessary tags
		textureTags = []
		selectionTags = {}
		for tag in tags:
			if c4d.Ttexture == tag.GetType():
				textureTags.append( tag ) 
			elif c4d.Tpolygonselection == tag.GetType():
				selectionTags[tag.GetName()] = tag
				print( "Found selection tag: %s" % tag.GetName() )
				pass
			pass

		polyCount = self.meshObj.GetPolygonCount()
		usedFaces = []

		# Ordering matters for restrictedTextureTags
		restrictedTextureTags = []
		if len( selectionTags ) > 0:
			uniqueSelections = []
			for textureTag in textureTags:
				if textureTag[c4d.TEXTURETAG_RESTRICTION] is not None:
					selectionName = textureTag[c4d.TEXTURETAG_RESTRICTION]
					if ( selectionName in selectionTags.keys() ) and ( selectionName not in uniqueSelections ):
						uniqueSelections.append( selectionName )
						restrictedTextureTags.append( textureTag )
						pass
					pass
				pass			
		else:
			# If there's only one texture tag, it will apply to all faces.
			if 1 == len( textureTags ):
				material = textureTags[0].GetMaterial()
				faces = [i for i in range( polyCount )]
				# decide if we should do U and V
				# print "tex tile x", textureTags[0][c4d.TEXTURETAG_TILESX], "tex tile y", textureTags[0][c4d.TEXTURETAG_TILESY]
				materialSets.append( { "material" : material, "faces" : faces, 
									   "repeat_u" : textureTags[0][c4d.TEXTURETAG_TILESX],
									   "repeat_v" : textureTags[0][c4d.TEXTURETAG_TILESY] } )

				usedFaces.extend( faces )
				pass

		# Process restrictedTextureTags in reverse
		for textureTag in reversed( restrictedTextureTags ):
			selectionName = textureTag[c4d.TEXTURETAG_RESTRICTION]
			selectedFaces = selectionTags[selectionName].GetBaseSelect()
			material = textureTag.GetMaterial()
			faces = []
			for faceIdx in range( polyCount ):
				if selectedFaces.IsSelected( faceIdx ) and ( faceIdx not in usedFaces ):
					faces.append( faceIdx )
					usedFaces.append( faceIdx )
				pass
			if len( faces ) > 0:

				print "tex tile x", textureTag[c4d.TEXTURETAG_TILESX], "tex tile y", textureTag[c4d.TEXTURETAG_TILESY]
				materialSets.append( { "material" : material, "faces" : faces,
									   "repeat_u" : textureTag[c4d.TEXTURETAG_TILESX],
									   "repeat_v" : textureTag[c4d.TEXTURETAG_TILESY] } )	
			pass

		unusedFaces = []
		for faceIdx in range( polyCount ):
			if faceIdx not in usedFaces:
				unusedFaces.append( faceIdx )
				pass
			pass

		if len( unusedFaces ) > 0:
			materialSets.append( { "material" : None, "faces" : unusedFaces,
								   "repeat_u" : None, "repeat_v" : None } )
			pass

		return materialSets
		pass

	def createTriMesh( self, polyObj, polyFaces ):
		# All polygons
		polys = polyObj.GetAllPolygons()		
		# Mesh points
		points = polyObj.GetAllPoints()		
		# Mesh normals
		normals = polyObj.CreatePhongNormals()
		# Mesh UVs
		uvwTag = polyObj.GetTag( c4d.Tuvw )
		# TriMesh
		triMesh = TriMesh()
		#colorRgb = [0.5, 0.5, 0.5]
		# Polygon faces attached to current material
		#polyFaces = materialFaces["faces"]
		for polyId in polyFaces:
			# Polygon
			poly = polys[polyId]
			# Polygon vertex indices, normals, and UVs for triangulation
			polyVerts = [poly.a, poly.b, poly.c]
			normalIdx = 4 * polyId
			polyNormals = [normals[normalIdx + 0], normals[normalIdx + 1], normals[normalIdx + 2] ]
			polyUvs = ["a", "b", "c"]
			if not poly.IsTriangle():
				polyVerts.append( poly.d )
				polyNormals.append( normals[normalIdx + 3] )
				polyUvs.append( "d" )
			# Number of triangles and poly relative indices
			numTris = len( polyVerts ) - 2
			fv0 = 0
			fv1 = 1
			fv2 = 2
			for i in range( numTris ):
				# Vertex indices
				mv0 = polyVerts[fv0]
				mv1 = polyVerts[fv1]
				mv2 = polyVerts[fv2]
				# Positions
				P0 = points[mv0] * _c4d.UNIT_SCALE 
				P1 = points[mv1] * _c4d.UNIT_SCALE 
				P2 = points[mv2] * _c4d.UNIT_SCALE 
				#print( "P0", P0 )
				#print( "P1", P1 )
				#print( "P2", P2 )
				# Normals
				N0 = polyNormals[fv0]
				N1 = polyNormals[fv1]
				N2 = polyNormals[fv2]
				#print( "N0", N0 )
				#print( "N1", N1 )
				#print( "N2", N2 )			
				# UV
				[u0,v0] = [0,0]
				[u1,v1] = [0,0]
				[u2,v2] = [0,0]
				if uvwTag is not None:
					uvwDict = uvwTag.GetSlow( polyId )
					if uvwDict is not None:
						uv0 = uvwDict[polyUvs[fv0]]
						uv1 = uvwDict[polyUvs[fv1]]
						uv2 = uvwDict[polyUvs[fv2]]
						#[u0,v0] = [1.0 -uv0.x, -uv0.y]
						#[u1,v1] = [1.0 -uv1.x, -uv1.y]
						#[u2,v2] = [1.0 -uv2.x, -uv2.y]
						[u0,v0] = [uv0.x, 1.0 - uv0.y]
						[u1,v1] = [uv1.x, 1.0 - uv1.y]
						[u2,v2] = [uv2.x, 1.0 - uv2.y]						
						pass
					pass
				#print( "%f, %f" % ( u0, v0 ) );
				# Vertex 0 data
				triMesh.appendPosition( P0[0], P0[1], P0[2] )
				triMesh.appendNormal( N0[0], N0[1], N0[2] )
				triMesh.appendTexCoord0( u0, v0 )
				# Vert[0] 1 data
				triMesh.appendPosition( P1[0], P1[1], P1[2] )
				triMesh.appendNormal( N1[0], N1[1], N1[2] )
				triMesh.appendTexCoord0( u1, v1 )
				# Vert[0] 2 data
				triMesh.appendPosition( P2[0], P2[1], P2[2] )
				triMesh.appendNormal( N2[0], N2[1], N2[2] )
				triMesh.appendTexCoord0( u2, v2 )
				colorRgb = [ 0.8, 0.8, 0.8 ]
				# TODO: how can we get vertex color info from the verts
				if colorRgb:
					triMesh.appendRgb( colorRgb[0], colorRgb[1], colorRgb[2] )
					triMesh.appendRgb( colorRgb[0], colorRgb[1], colorRgb[2] )				
					triMesh.appendRgb( colorRgb[0], colorRgb[1], colorRgb[2] )
				# Increment to next triangle
				fv1 += 1
				fv2 += 1				
				pass
			pass

		# Return
		return triMesh
		pass	
	## class BaseMesh
	pass

## \class BaseCamera
#
#
class C4DCamera( BaseCamera ):
	## c'tor
	def __init__( self, cameraInfo ):
		#print( "BaseCamera c'tor" )	
		BaseCamera.__init__(self)
		self.name = cameraInfo.GetName()
		self.projectionType = cameraInfo[c4d.CAMERA_PROJECTION]
		# ugly but that's c4d
		doc = c4d.documents.GetActiveDocument()
		renderData = doc.GetActiveRenderData()
		aspectRatio = renderData[c4d.RDATA_FILMASPECT]

		if self.projectionType == c4d.Pperspective:
			# TODO: How do we get aspect ratio
			self.projectionType = BaseCamera.PROJECTION
			self.aspectRatio = aspectRatio
			self.yfov = cameraInfo[c4d.CAMERAOBJECT_FOV_VERTICAL]
			self.cameraType = BaseCamera.PROJECTION
		# TODO: how do we figure out if this is an orthographic
		else:
			# TODO: How do we get xmag, ymag
			self.projectionType = BaseCamera.ORTHOGRAPHIC
			self.xmag = 1
			self.ymag = 1
			self.cameraType = BaseCamera.ORTHOGRAPHIC

		self.zfar = cameraInfo[c4d.CAMERAOBJECT_FAR_CLIPPING]
		self.znear = cameraInfo[c4d.CAMERAOBJECT_NEAR_CLIPPING]	
		pass
	## class BaseCamera
	pass

## \class BaseLight
#
#
class C4DLight( BaseLight ):
	## c'tor
	def __init__( self, obj ):
		#print( "BaseLight c'tor" )
		BaseLight.__init__(self)	
		self.name = obj.GetName()	
		pass
	## class BaseLight
	pass	

class C4DNode( BaseNode ):
	## c'tor
	def __init__( self, obj ):
		#print( "C4DNode c'tor" )
		BaseNode.__init__( self )	
		self.obj = obj
		self.name = self.obj.GetName()
		# extract transformation
		self.extractTranform()
		# cache attributes
		self.determineCacheAttributes()
		# cache attributes
		self.determineAnimation()
		# append children
		childBegIt = self.obj.GetDown()
		while childBegIt:
			self.childNodes.append( C4DNode( childBegIt ) )
			childBegIt = childBegIt.GetNext()
			pass
		pass

	def extractTranform( self ):
		# cache the relative matrix
		self.matrix = convertC4DMatrix( self.obj.GetMl() )
		trans = self.obj.GetRelPos()
		self.translation = [ trans.x, trans.y, trans.z ]
		scale = self.obj.GetRelScale()
		self.scale = [ scale.x, scale.y, scale.z ]
		# NOTE: HPB rotation euler need to convert
		rot = self.obj.GetRelRot()
		self.rotation = [ rot.x, rot.y, rot.z ]
		pass

	def determineAnimation( self ):
		track = self.obj.GetFirstCTrack() #Get it's first animation track 
		if not track: 
			return # if it doesn't have any tracks. End the script
		curve = track.GetCurve() #Get the curve for the track found
		count = curve.GetKeyCount() #Count how many keys are on it
		print count, str(curve)
		pass

	def determineCacheAttributes( self ):
		objType = self.obj.GetType()
		doc = c4d.documents.GetActiveDocument()
		if _c4d.OBJECT_BASE_MESH == objType:
			self.cacheAsMeshNode( self.obj )
		else:
			if objType in meshObjects:
				tmpObj = self.obj.GetClone()
				tmpList = c4d.utils.SendModelingCommand( command = c4d.MCOMMAND_CURRENTSTATETOOBJECT, list = [tmpObj], 
														 mode = c4d.MODELINGCOMMANDMODE_ALL, doc = doc )
				c4d.utils.SendModelingCommand( command = c4d.MCOMMAND_TRIANGULATE, list = tmpList, doc = doc )

				if len( tmpList ) > 0:
					self.cacheAsMeshNode( tmpList[0] )
				else:
					print("problem converting mesh node: " + getName())
					pass
			else:
				if objType == _c4d.OBJECT_CAMERA:
					self.cacheAsCameraNode()
				elif objType == _c4d.OBJECT_LIGHT:
					self.cacheAsLightNode()
				elif objType == _c4d.OBJECT_NULL:
					self.cacheAsNullNode()
				else:
					print( "Unsupported object %s (type=%d)" % ( obj.GetName(), obj.GetType() ) )
					obj = None
				pass
			pass
		if not self.cached:
			print( "Unsupported object %s (type=%d)" % ( obj.GetName(), obj.GetType() ) )
			pass
		pass

	# we take an object here because we may have cloned and modeled the obj
	def cacheAsMeshNode( self, obj ):
		# this would be where we'd determine how many meshes we'd want
		self.hasMesh = True	
		self.cached = True 
		self.meshes.append( C4DMesh( obj ) )
		pass

	def cacheAsCameraNode( self ):
		self.hasCamera = True
		self.cached = True
		self.camera = C4DCamera( self.obj )
		pass

	def cacheAsLightNode( self ):
		self.hasLight = True
		self.cached = True
		self.light = C4DLight( self.obj )
		pass

	def cacheAsNullNode( self ):
		self.isNull = True
		self.cached = True
		# cache the few attributes, possibly this isn't needed
		pass

	## class BaseLight
	pass	