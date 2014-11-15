import os
import mechanize
from bs4 import BeautifulSoup
import FileStoreDatabase
import datetime
import pprint

class PatchDownloader:
	DebugLevel = 3
	ShowErrorMessage = True
	def __init__( self, download_folder, databasename = None ):
		self.DownloadFolder = download_folder
		if not os.path.isdir( self.DownloadFolder ):
			os.makedirs( self.DownloadFolder )

		if databasename!=None:
			self.Database = FileStoreDatabase.Database( databasename )
		else:
			self.Database = None

		self.BR = mechanize.Browser()

	def DownloadFileByLink( self, link ):
		family_id = self.GetFamilyID( link )
		if family_id:
			return self.DownloadFileByFamilyID( family_id )
		return None

	def DownloadFileByFamilyID( self, family_id ):
		return self.DownloadFileByConfirmationLink( 'http://www.microsoft.com/downloads/en/confirmation.aspx?familyId=' + family_id + '&displayLang=en' )
		
	def DownloadFileByConfirmationLink( self, link ):
		try:
			data = self.BR.open( link ).get_data()
		except:
			return []

		if self.DebugLevel > 3:
			print '='*80
			print link
			print data

		files = []
		soup = BeautifulSoup( data )
		for anchor in soup.findAll( "a" ):
			for name, download_link in anchor.attrs:
				if anchor.text == 'Start download' and name =='href':
					print  'Found Start download'
					filename = download_link[download_link.rfind("/")+1:]
					filename = os.path.join( self.DownloadFolder, filename )
					if self.DebugLevel > -3:
						print '\t\t',download_link,'->',filename

					try:
						if not os.path.isfile( filename ):
							data = self.BR.open( download_link ).get_data()

							if data and len( data ) > 0:
								fd = open( filename, "wb" )
								fd.write( data )
								fd.close()
						files.append( filename )
					except:
						print 'Failed to download', download_link
		return files

	def GetFamilyID( self, link ):
		family_id = None
		if link:
			pos = link.lower().find("familyid=")
			if  pos >=0:
				family_id = link[pos+len( 'familyid=' ):]
				ampersand_pos = family_id.find("&")
				if ampersand_pos >= 0:
					family_id = family_id[:ampersand_pos]

				if self.DebugLevel > 3:
					print '\t',link
					print '\t',family_id
					print ''
		return family_id

	def DownloadMSPatch( self, year, bulletin_number, download_patch_files = False ):
		url = 'https://technet.microsoft.com/en-us/library/security/ms%.2d-%.3d.aspx' % ( year, bulletin_number )

		print 'Opening %s' % url
		try:
			data = self.BR.open( url ).get_data()
		except:
			if self.ShowErrorMessage:
				print 'Downloading Failed'
			return None

		print 'Downloaded %d bytes' % len(data)
		cache_filename='MS%.2d-%.3d.html' % ( year, bulletin_number )
		fd=open(cache_filename,"w")
		fd.write(data)
		fd.close()

		return self.ParseBulletin(data, url, 'MS%.2d-%.3d' % ( year, bulletin_number ))

	def ParseTable(self,start_tag):
		# Go through each tr and td inside them
		table_info=[]
		tr_members = []
		if table_tag:
			for tr in table_tag.findAll( "tr" ):
				td_members = []
				for td in tr.findAll( "td" ):
					td_member = {}
					td_member['text'] = ''
					url_str = ''
					if td.string:
						td_member['text'] = td.string
					for tag in td.findAll(True):
						if tag.name == 'a':
							td_member['url']  = tag.attrs['href']
						if tag.string:
							td_member['text'] += tag.string
					
					td_members.append( td_member )
				tr_members.append( td_members )

		for td_members in tr_members[1:]:
			column = 0 
			td_member_hash = {}
			for td_member in td_members:

				td_member_hash[ tr_members[0][column]['text'] ] = td_member
				column += 1

			table_info.append( td_member_hash )
			"""
				url = None
				if td_member.has_key( 'url' ):
					url = td_member['url']

				family_id = self.GetFamilyID( url )
				if download_patch_files:	
					if family_id:
						td_member['files'] = self.DownloadFileByFamilyID( family_id )
				elif family_id:
					td_member['files'] = ( family_id )
			"""
					
			if self.DebugLevel > -3:
				pprint.pprint(table_info)

		return table_info

	def ParseBulletin(self,data, url='', label='', download_patch_files=False):
		soup = BeautifulSoup( data )

		title = ''
		for h1_tag in soup.find( "h1" ):
			title = h1_tag.string

		for h2_tag in soup.find( "h2" ):
			title += h2_tag.string

		patch_info = {}
		patch_info['label'] = label
		patch_info['url'] = url
		patch_info['title'] = title

		#Retrieve CVEs
		CVEs=[]
		for h2_tag in soup.findAll( "h2" ):
			if h2_tag.string == 'Vulnerability Information':
				current_tag = h2_tag.nextSibling
				while 1:
					if current_tag.name == 'h2':
						break
					for h3_tag in current_tag.findAll('h3'):
						cve_pos = h3_tag.string.find('CVE-')
						if cve_pos >= 0:
							if self.DebugLevel > 3:
								print h3_tag.string
							cve_str=h3_tag.string[cve_pos:cve_pos+13]
							CVEs.append( ( cve_str, h3_tag.string ) )
					current_tag = current_tag.nextSibling

		for h3_tag in soup.findAll( "h3" ):
			if h3_tag.string == 'Vulnerability Details':
				print 'h3_tag',h3_tag.string
				pass

		for table_tag in soup.findAll( "table" ):
			for tr in table_tag.findAll( "tr" ):
				for td in tr.findAll( "td" ):
					print 'td: [%s]' % td.getText()
					break
				break

		patch_info['CVE'] = CVEs
		patch_info['HtmlData'] = data

		affected_software_table_infos=[]
		for h3_tag in soup.findAll( "h3" ):
			if h3_tag.text == 'Affected Software' or h3_tag.text == 'Affected Software:' or h3_tag.text == 'Affected Components:':
				# Find affected software table
				current_tag=h3_tag.nextSibling
				while current_tag:
					try:
						if current_tag.name=='table':
							affected_software_table_infos.append(self.ParseTable(current_tag))
					except:
						pass
					current_tag = current_tag.nextSibling

		return ( patch_info, affected_software_table_infos )

	def DownloadMSPatchAndIndex( self, year, bulletin_number, download_patch_files = False ):
		name = 'MS%.2d-%.3d' % ( year, bulletin_number )

		if self.Database!=None:
			if self.Database.GetPatch( name ):
				return ( {},{} )

		print 'Downloading',name
		ret = self.DownloadMSPatch( year, bulletin_number, download_patch_files )

		if not ret:
			if self.ShowErrorMessage:
				print 'Nothing to do'
			return ret

		(patch_info, affected_software_table_info) = ret
		
		if self.Database!=None:
			patch = self.Database.AddPatch( patch_info['label'], patch_info['title'], patch_info['url'], patch_info['HtmlData'] )

			for (cve_str, name) in patch_info['CVE']:
				self.Database.AddCVE( patch, cve_str, name )

		for td_member_hash in affected_software_table_info:
			for ( column_text, td_member ) in td_member_hash.items():
				if td_member.has_key( 'files' ):
					if self.DebugLevel > 3:
						for ( name, data ) in td_member.items():
							print '\t', name, data
						
					if td_member_hash.has_key( 'Operating System' ):
						operating_system = td_member_hash['Operating System']['text']
					else:
						operating_system = td_member['text']

					if self.DebugLevel > 3:
						print operating_system 
						print td_member['text']
						print td_member['url']
						print td_member['files'][0]
						if td_member_hash.has_key('Maximum Security Impact'):
							print td_member_hash['Maximum Security Impact']['text']
						if td_member_hash.has_key('Aggregate Severity Rating'):
							print td_member_hash['Aggregate Severity Rating']['text']

					bulletins_replaced = ""
					if td_member_hash.has_key( 'Bulletins Replaced by This Update' ):
						bulletins_replaced = td_member_hash['Bulletins Replaced by This Update']['text'] 
					if td_member_hash.has_key( 'Bulletins Replaced by this Update' ):
						bulletins_replaced = td_member_hash['Bulletins Replaced by this Update']['text'] 

					maximum_security_impact = ''
					
					if td_member_hash.has_key('Maximum Security Impact') and td_member_hash['Maximum Security Impact'].has_key('text'):
						maximum_security_impact = td_member_hash['Maximum Security Impact']['text']
					
					aggregate_severity_rating = ''
					if td_member_hash.has_key('Aggregate Severity Rating') and td_member_hash['Aggregate Severity Rating'].has_key('text'):
						aggregate_severity_rating = td_member_hash['Aggregate Severity Rating']['text']

					filename = ""
					if td_member.has_key( 'files' ) and len(td_member['files']) > 0:
						filename = td_member['files'][0]

					if self.DebugLevel > 2:
						print 'Calling AddDownload', patch, filename

					if self.Database!=None:
						self.Database.AddDownload( 
							patch, 
							operating_system, 
							td_member['text'], 
							td_member['url'], 
							filename,
							maximum_security_impact,
							aggregate_severity_rating,
							bulletins_replaced 
						)

		if self.Database!=None:
			if not self.Database.Commit():
				print 'Failed Downloading',name
		return ret

	def DownloadPatches( self, start_year, start_number, end_year, end_number ):
		print start_year, start_number, end_year, end_number
		for year in range( start_year, end_year+1 ):
			current_start_number = 1
			current_end_number = 999
			if year == start_year:
				current_start_number = start_number
			elif year == end_year:
				current_end_number = end_number
			
			for patch_number in range( current_start_number, current_end_number):
				print 'Checking for MS%.2d-%.3d' % ( year, patch_number )
				ret = self.DownloadMSPatchAndIndex( year, patch_number )
				if ret == None:
					break
		return

	def DownloadCurrentYearPatches( self ):
		now = datetime.datetime.now()
		year = now.year - 2000
		return self.DownloadPatches( year, 1, year, 999 )

if __name__ == '__main__':
	patch_downloader = PatchDownloader( "Patches" )
	#patch_downloader.DownloadCurrentYearPatches()

	fd=open('MS14-001.html','r')
	data=fd.read()
	fd.close()
	patch_downloader.ParseBulletin(data)