##==============================================================================================================================================================
## Date: 30 Jan 2017
## Author: Naveed Nadvi
## Description: Asks user to select a list of Scopus EIDs and returns a CSV file with list of publication related data
## Directions:
##-------------------------------------------------------------------------
##	Type the following to start Python:
##										C:\Python34\python.exe
##-------------------------------------------------------------------------
## Copy everything in this file to Windows prompt/Python terminal.
##
## NOTE: working directory is set below to: "C:\\Users\\nnad2024\\Documents\\LOCAL_COPIES\\PythonResults(local)\\temp_results_folder"
## Note the double '\' needed to define the path. 
## Please change this to your desired directory as required.
## The program is run by typing:
## 								
##								MAIN_EID()
##
##
## NOTE: At the end of execution, look carefully at entries in problem_EIDs_ARRAY2. Run these EIDs through the web interface
## 		 to confirm all remaining EIDs in this list ARE invalid/illegal. If not, re-run the script with this list and append 
##		 the CSV outputs to the main CSV.
##
##==============================================================================================================================================================
'''
BASIC FLOWCHART:

read a list of scopusIDs (EIDs).
	store the list into an array.
initiate log files and global arrays and variables
in blocks of 25 (max allowable for data harvest when view=COMPLETE) do the following:
	generate the URL {only the EIDs will change, all other parameters stay the same}
	store the URL_output
	parse the URL_output as follows:
		create array of EIDs (max will be 25, but CAN be less): extractXML with <entry> tags
		for every EID harvest data: extractXML with individual tags

			•         EID
			•         DOI
			•         PubORCID
			•         PubmedID
			•         Title
			•         PubDate
			•         Abstract
			•         AuthKeywords
			•         FirstAuthor
			•         No. of authors
			•         Source Title (journal/Article name)
			•         ISSN
			•         eISSN
			•         ISBN
			•         Volume
			•         Issue
			•         PageRange == ideally split Start Page and End Page
			•         Scopus Document Type == ideally as: aggregationType|subtypeDescription
			•         CitedBy
			•         AuthorsList == ideally have one row per AuthName, AU-ID, AuORCID, AF-ID, Au_url
			•         AffiliationList == ideally have one row per AF-ID, AfName, City, Country, Aff_url
			•         FundingDetails == ideally have one row per fund-sponsor, fund-acr, fund-no
			

			this is where it will be easier to check for missing data and if needed, assigning 'noData' value
			pubs can have multiple authors AND multiple afids- SEE IF THIS CAN BE HARVESTED *PER ROW*
			
	store problem records (XML and other errors)
reprocess problem records
finalise error logs and outputs and print arrays

'''
#!/usr/bin/python

##======================================================================================================================================
## IMPORTATION AND PROXY SETTINGS: SAME FOR MOST OTHER SCRIPTS
##------------------------------------------------------------------------------------------------------------------------------
import os
import urllib.request
import csv
import time
import datetime
import re
import tkinter, tkinter.filedialog # used for selecting file with dialog box
import urllib.error
import itertools

import pandas as pd ## At the moment works ONLY within Spyder (ANNACONDA)

proxy_support = urllib.request.ProxyHandler({"http":"web-cache-ext.usyd.edu.au:8080"}) ## Use USYD proxy server
opener = urllib.request.build_opener(proxy_support) ## Build Proxy server
urllib.request.install_opener(opener) ## Install Proxy server
##======================================================================================================================================



##======================================================================================================================================
## DEFINING DEFAULT GLOBAL VARIABLES AND WORKING DIRECTORIES SPECIFIC FOR THIS SCRIPT
##------------------------------------------------------------------------------------------------------------------------------
os.chdir("C:\\SET YOUR OWN DIRECTORY") ## change working directory

#defaultScopusID = '84954411735' ## this is one of Naveed's ScopusID. '84860316803' is Rich's scopusID
defaultEID = '2-s2.0-84953366816' # -- NAN's Structure paper; '2-s2.0-6666666666' is a test for an EID that is not legal (0 results returned)
defaultItemsPerPage = 25 ## this should stay at 25 (for COMPLETE view) and ONLY reduced if there are other issues
defaultEncodingFormat = 'utf-8'
defaultAPI_Key = "6aa99ca6xx1094cbc56ae668717bac664" ## This is a random API key. Not sure if it is valid!

elsevierScopusSearchToken = "http://api.elsevier.com/content/search/scopus?" ## other specific search tokens can be stored for ease
#ScopusSearchFieldFilters= "prism:doi,eid,dc:title,prism:coverDate" ## this is not needed as we will be harvesting almost all tagged-data
viewEID = '&view=COMPLETE' ## view can be 'STANDARD' (max 25 items per page), 'COMPLETE' (max 25 items per page). Need COMPLETE to pull ALL data
responseGenerator = '&httpAccept=application/xml' ## this parameter determines the type of output that is generated (e.g. JSON or XML)
##======================================================================================================================================



##======================================================================================================================================
## DEFINING START AND END TAGS SPECIFIC FOR THIS SCRIPT
## NOTE: This script generates output in XML format so that the start and end tags are easily identifiable
##
## array of start- and end-tags are structured as follows: [<startTag>,<endTag>, 'dataDescription']
##
##------------------------------------------------------------------------------------------------------------------------------
START_END_TAGS_ARRAY = [
						['<opensearch:totalResults>', '</opensearch:totalResults>', 'totalResults'],
						['<entry>', '</entry>', 'PubEntries'],
						['<eid>', '</eid>', 'pubEID'],
						['<prism:doi>', '</prism:doi>', 'PubDOI'],
						['<orcid>', '</orcid>', 'PubORCID'],
						['<pubmed-id>', '</pubmed-id>', 'PubmedID'],
						['<dc:title>', '</dc:title>', 'PubTitle'],
						['<prism:coverDate>', '</prism:coverDate>', 'PubDate'],
						['<dc:description>', '</dc:description>', 'Abstract'],
						['<authkeywords>', '</authkeywords>', 'AuthorKeywords'],
						['<dc:creator>', '</dc:creator>', 'FirstAuthor'],
						['<author-count limit="100" total=', '</author-count>', 'TotalAuthors'],
						['<prism:publicationName>', '</prism:publicationName>', 'SourceTitle(JournalName)'],
						['<prism:issn>', '</prism:issn>', 'PubISSN'], ## need to correctly format with a '-' between 4th and 5th position to generate a 9-character value
						['<prism:eIssn>', '</prism:eIssn>', 'Pub_eISSN'], ## need to correctly format with a '-' between 4th and 5th position to generate a 9-character value
						['<prism:isbn>', '</prism:isbn>', 'PubISBN'], ## the ISBN does NOT have a stringent format like e/ISSN
						['<prism:volume>', '</prism:volume>', 'Volume'],
						['<prism:issueIdentifier>', '</prism:issueIdentifier>', 'Issue'],
						['<prism:pageRange>', '</prism:pageRange>', 'PageRange'], ## further manipulation is NOT necessary, and can be done in Excel
						['<prism:aggregationType>', '</prism:aggregationType>', 'DocumentType1'],
						['<subtypeDescription>', '</subtypeDescription>', 'DocumentType2'], ## ideally as: aggregationType|subtypeDescription
						['<citedby-count>', '</citedby-count>', 'Count_of_citing_documents'],
						['<author seq=', '</author>', 'AuthorList'], ## further manipulation NEEDED for author as Au_name, Au-ID, AuORCID, AF-IDList, Au_url
						['<affiliation>', '</affiliation>', 'AffiliationList'], ## further manipulation NEEDED with one row per AfName, AF-ID, City, Country, Aff_url
						['<fund-sponsor>', '</fund-sponsor>', 'FunderSponsorList'] ## further manipulation NEEDED: ideally have one row per fund-sponsor, fund-acr, fund-no
					]

##======================================================================================================================================



##======================================================================================================================================
## THE FOLLOWING ARRAYS ARE SPECIFIC FOR THIS SCRIPT AND SHOULD NEVER BE RESET OR REPLACED!!!
##------------------------------------------------------------------------------------------------------------------------------
## <---------$$$$$$$$$$$ Need to create/modify code here
HEADER = [
			'PubEID',
			'PubDOI',
			'PubORCID',
			'PubmedID',
			'PubTitle',
			'PubDate',
			'Abstract',
			'AuthorKeywords',
			'FirstAuthor',
			'TotalAuthors',
			'SourceTitle(JournalName)',
			'PubISSN',
			'Pub_eISSN',
			'PubISBN',
			'Volume',
			'Issue',
			'PageRange',
			'DocumentType1',
			'DocumentType2',
			'Count_of_citing_documents',
			'AuthorList',
			'AffiliationList',
			'FunderSponsorList'
		]

LOG_FILE_ARRAY = [
					'EID_extract_xml_data_error_file','EID_E404_invalid_queries'
					,'EID_E400_error_file_maximum_request_exceeded'
					,'EID_E500_error_file_back-end_processing_error'
					,'EID_other_error_file'
					,'EID_another_error_file_non_http_other_errors'
					,'EID_data_error_file'
					,'check_processed_records_from_all_EID'
					,'#final_summary_EIDs'
					,'error_file_problem_URL_ARRAY' ## this file is only created to store the raw URLs, which by itself is not very useful
					,'error_file_problem_URL_ARRAY2' ## this file is only created to store the raw URLs, which by itself is not very useful
				]
##======================================================================================================================================



##======================================================================================================================================
## THE FOLLOWING GLOBAL VARIABLES STORE VALUES DURING PROGRAM EXECUTION AND NEEDS TO BE RESET FOR THE NEXT EXECUTION
##------------------------------------------------------------------------------------------------------------------------------
EID_LIST = [] ## stores EIDs from the input file to memory
problem_EIDs_ARRAY = [] ## to store EIDs with errors -- this is BETTER than storing problem_URLs because each URL is composed of multiple EIDs, some of which may be successful
successful_EIDs_ARRAY = [] ## to store successfully processed EIDs -- this is BETTER than storing problem_URLs because each URL is composed of multiple EIDs, some of which may be successful
problem_EIDs_ARRAY2 = [] ## to store if new errors come up during re-processing
successful_EIDs_ARRAY2 = [] ## to store successfully processed EIDs during re-processing

problem_URL_ARRAY2 = []
unique_problem_URL_ARRAY2 = []

EID_AFILLIATIONS_ARRAY = []
EID_AUTHORS_ARRAY = []
EID_FUNDERS_ARRAY = []

unique_problem_EIDs_ARRAY = [] ## to store unique EIDs with errors
unique_successful_EIDs_ARRAY = [] ## to store unique successful EIDs
unique_problem_EIDs_ARRAY2 = [] ## to store if new errors come up during re-processing
unique_successful_EIDs_ARRAY2 = [] ## to store successful unique EIDs during re-processing

DATA_WRITTEN_TO_CSV = [] ## to store row-data written to csv
UNIQUE_DATA_WRITTEN_TO_CSV = [] ## to store UNIQUE row-data written to csv

API_KEY_USAGE = 0 ## this counter stores the usage for the given API key
EID_COUNTER = 0 ## this counter stores the successful EIDs processed so far
EIDS_IN_FILE = 0 ## this variable stores the number of EIDs present in the supplied file.

##======================================================================================================================================



def write_to_file(filename = "no Filename defined yet.txt", stringToWrite = "stringToWrite not defined yet"):
	len_fn = len(filename)
	len_txt = len('.txt')
	filename_extension = filename[(len_fn-len_txt):] ## a right() like splicing to extract last 4 characters
	if filename_extension != '.txt':
		filename = filename+'.txt' ## this ensures if a .txt filename has NOT been defined, then the file is created as .txt
	
	file_to_write = open(filename,'a')
	#file_to_write.write(stringToWrite+'\n')
	file_to_write.write(stringToWrite)
	file_to_write.write('\n')
	file_to_write.close()
	return;

## This function takes a data array and returns only the unique elements in the array as another list/array. FUNCTION DOES NOT PRESERVE ORDER OF ELEMENTS
## This function WORKS for arrays of basic data types (e.g. strings or ints) and ALSO for arrays of array: [1,2,3,1,3,4], ['a','b','a','d','e'], ['1','2','d','e'], [[1,2],[2,3],[1,2],[4]])
## NOTE!!! this function will ONLY work when the nonUnique_ARRAY contains data of the SAME type (e.g. array of only int or string OR array of int_array or string_array: [1,2,3,'a','b'] or [[1,2],[2,3],['1,2'],[4]] are illegal)
## This funciton will not work if the array or the composite array of array contains data of mixed type.
def uniquify_Array(nonUnique_ARRAY):
	nonUnique_ARRAY.sort()
	unique_ARRAY = list(nonUnique_ARRAY for nonUnique_ARRAY,_ in itertools.groupby(nonUnique_ARRAY))
	return unique_ARRAY;

def select_file_and_initiate_variables():
## 1. Open a file containing list of EIDs (one line of EID per row)
	root = tkinter.Tk()
	root.withdraw()
	filename_location = tkinter.filedialog.askopenfilename() # user select input file
	
	reset_global_variables_and_logfiles()
	
	EID_File = open(filename_location,'r')  ## Open text file containing the list
	file_to_write = "#final_summary_EIDs.txt"
	number_of_EIDs = 0
	nonUnique_EID_LIST = []
	for line in EID_File:
		EID = line.strip() ## removes any newline characters and whitespaces
		if len(EID) > 7 and EID != '': ## len of '2-s2.0' is 7. ALL valid EIDs MUST be greater than 7 in length
			nonUnique_EID_LIST.append(EID)
			number_of_EIDs = number_of_EIDs + 1
			
	if number_of_EIDs == 0:
		print("Warning: File has no EIDs!!!")
		stringToWrite = "Warning: File has no EIDs!!!"
		write_to_file(file_to_write,stringToWrite)
		
	else: 
		global EID_LIST
		EID_LIST = uniquify_Array(nonUnique_EID_LIST)
		
		global EIDS_IN_FILE
		EIDS_IN_FILE = len(EID_LIST)
		
		print('\n'+str(EIDS_IN_FILE)+" UNIQUE EID(s) to process ("+str(number_of_EIDs)+" were supplied in file).")
		stringToWrite = str(EIDS_IN_FILE)+" UNIQUE EID(s) to process ("+str(number_of_EIDs)+" were supplied in file)."
		write_to_file(file_to_write,stringToWrite)
		
	return filename_location;

## this function, run at the start of execution is needed if the same script is re-run at the prompt.
## If not reset, the values of the global variables from the previous run remain stored in memory.
def reset_global_variables_and_logfiles(): ## <---------$$$$$$$$$$$ Need to create/modify code here
	print("Initiating all log files - not all (error) files may have records:")
	now = datetime.datetime.now()
	
	for logfile in LOG_FILE_ARRAY:
		filename = logfile+'.txt'
		print("\t"+filename)
		stringToWrite = "\n========NEW RECORDS: "+now.strftime("%Y%m%d_%H:%M:%S")+"========-----------------\n\n"
		write_to_file(filename,stringToWrite)
	
	print("\nResetting the global ARRAYs and COUNTER VARIABLEs.")
	
	EID_LIST[:] = [] ## resetting to store new EIDs from new input file to memory
	problem_EIDs_ARRAY[:] = [] ## resetting to store EIDs with errors for the following execution
	successful_EIDs_ARRAY[:] = [] ## resetting to store successful EIDs for the following execution
	problem_EIDs_ARRAY2[:] = [] ## resetting to store if new errors come up during re-processing for the following execution
	successful_EIDs_ARRAY2[:] = [] ## resetting to store successful EIDs during re-processing for the following execution
	
	problem_URL_ARRAY2[:] = []
	unique_problem_URL_ARRAY2[:] = []
	
	EID_AFILLIATIONS_ARRAY[:] = []
	EID_AUTHORS_ARRAY[:] = []
	EID_FUNDERS_ARRAY[:] = []
	
	unique_problem_EIDs_ARRAY[:] = [] ## resetting to store unique EIDs with errors for the following execution
	unique_successful_EIDs_ARRAY[:] = [] ## resetting to store unique successful EIDs for the following execution
	unique_problem_EIDs_ARRAY2[:] = [] ## resetting to store if new errors come up during re-processing for the following execution
	unique_successful_EIDs_ARRAY2[:] = [] ## resetting to store successful unique EIDs during re-processing for the following execution
	
	DATA_WRITTEN_TO_CSV[:] = [] ## resetting to store row-data written to csv for the following execution
	UNIQUE_DATA_WRITTEN_TO_CSV[:] = [] ## resetting to store UNIQUE row-data written to csv for the following execution
	
	global API_KEY_USAGE ## specifying the GLOBAL VARIABLE
	API_KEY_USAGE = 0
	global EID_COUNTER
	EID_COUNTER = 0
	global EIDS_IN_FILE
	EIDS_IN_FILE = 0
	
	len_and_values_after_reset = int(EIDS_IN_FILE+EID_COUNTER+API_KEY_USAGE
									+len(DATA_WRITTEN_TO_CSV)+len(UNIQUE_DATA_WRITTEN_TO_CSV)
									+len(successful_EIDs_ARRAY)+len(problem_EIDs_ARRAY2)+len(successful_EIDs_ARRAY2)
									+len(unique_problem_EIDs_ARRAY)+len(unique_successful_EIDs_ARRAY)+len(unique_problem_EIDs_ARRAY2)
									+len(unique_successful_EIDs_ARRAY2)+len(EID_LIST)+len(problem_EIDs_ARRAY)+len(problem_URL_ARRAY2)
									+len(unique_problem_URL_ARRAY2)+len(EID_AFILLIATIONS_ARRAY)+len(EID_AUTHORS_ARRAY)+len(EID_FUNDERS_ARRAY))
									
	print("\nConfirming reset: Total length of ARRAYs & VARIABLE values = "+str(len_and_values_after_reset)+" (should be ZERO)\n")
	filename = "#final_summary_EIDs.txt"
	stringToWrite = "Confirming reset: Total length of ARRAYs & VARIABLE values = "+str(len_and_values_after_reset)+" (should be ZERO)"
	write_to_file(filename,stringToWrite)
	return;

def getArgumentValues():
# #=======================================================
# # NOTE!!!
# # REMOVE THE '##' to implement interactivity.
# #=======================================================
	argumentValues = ['APIkey', 'encodingFormat'] ## defining an array of TWO elements that will contain the values for the API key and other arguments
	#now = datetime.datetime.now()
		
	##apiKey = input("Please provide API Key or hit ENTER to use default (Naveed's) key: ")
	apiKey = defaultAPI_Key ## This is a random API key. 
	
	##encodingFormat = input("Enter the encoding format as string or press ENTER to use default ('utf-8'): ")
	encodingFormat = defaultEncodingFormat ## !!!NOTE!!! Default value of 'utf-8' is enforced for now. This line should be commented out if subsequent manipulations are done/needed
	
	argumentValues[0] = apiKey
	argumentValues[1] = encodingFormat
	
	print('\nWe now have all data needed to generate the CSV file! Here is a summary:')
	print('APIkey = '+str(apiKey)+', \nEncodingFormat = '+str(encodingFormat))
	
	return argumentValues;

def write_data_to_CSV(csvwriter, data_array_to_write):
	csvwriter.writerow(data_array_to_write[0:len(data_array_to_write)])
	return;

## t = generate_header()
def generate_header(csvwriter, suppliedHeader = ''):
	if suppliedHeader == '':
		suppliedHeader = HEADER
	write_data_to_CSV(csvwriter,suppliedHeader) ## HEADER is a GLOBAL ARRAY
	return suppliedHeader; ## THIS IS THE HEADER.

#typical URL= http://api.elsevier.com/content/search/scopus?query=%28eid%282-s2.0-63549114141%29+OR+eid%282-s2.0-38849112567%29+OR+eid%282-s2.0-67650395644%29+OR+eid%282-s2.0-57149109402%29+OR+eid%282-s2.0-84897664337%29+OR+eid%282-s2.0-55649120237%29+OR+eid%282-s2.0-71849109661%29+OR+eid%282-s2.0-70349779598%29+OR+eid%282-s2.0-66749105081%29+OR+eid%282-s2.0-70350230397%29+OR+eid%282-s2.0-71549157774%29+OR+eid%282-s2.0-73549112416%29+%29&view=COMPLETE&httpAccept=application/xml&apiKey=7f592e39046a1428efc18dbf075455fc

## t = generate_EID_URL() ## <---------$$$$$$$$$$$ Need to create/modify code here
def generate_EID_URL(EID_List_to_Process, reprocessTag = 'N', apiKey = defaultAPI_Key):
	# elsevierScopusSearchToken = "http://api.elsevier.com/content/search/scopus?" ## other specific search tokens can be stored for ease
	# viewEID = '&view=COMPLETE'
	# responseGenerator = '&httpAccept=application/xml'
	
	URL = "valid url not defined yet"
	
	EIDs = len(EID_List_to_Process)	
	if EIDs > 0 and EIDs <= 25:
		EID_String = ''
		for i in range(0,EIDs):
			EID = EID_List_to_Process[i]
			if i < EIDs-1: ## there are more records
				string = '+eid%28'+str(EID)+'%29+OR' ## append an 'OR' clause if the EID is NOT the last entry
			else: ## this is the last record
				string = '+eid%28'+str(EID)+'%29+' ## do NOT append an 'OR' clause if the EID is the last entry
			EID_String = EID_String + string
			
		queryEID = 'query=%28'+str(EID_String)+'%29'
		URL = elsevierScopusSearchToken + queryEID + viewEID + responseGenerator + "&apiKey="+apiKey
	
	else: ## any other illegal values --SHOULD NEVER HAPPEN
		print("\nWarning: EID_List_to_Process is empty OR more than 25 EIDs provided.")
		print(" List CAN be empty if ALL remaining EIDs are ILLEGALs before \nnumber_of_iterations has been completed.")
		if reprocessTag == 'N':
			print("  These missed EIDs will be reprocessed.\n")
	#print ('generatedURL:\n',URL)
	return URL;

## t = output_from_URL('http://api.elsevier.com/content/search/scopus?query=%28%28eid%282-s2.0-63549114141%29+OR+eid%282-s2.0-38849112567%29+OR+eid%282-s2.0-67650395644%29+OR+eid%282-s2.0-57149109402%29+OR+eid%282-s2.0-84897664337%29	+OR+eid%282-s2.0-55649120237%29+OR+eid%282-s2.0-71849109661%29+OR+eid%282-s2.0-70349779598%29+OR+eid%282-s2.0-66749105081%29+OR+eid%282-s2.0-70350230397%29+OR+eid%282-s2.0-71549157774%29+OR+eid%282-s2.0-73549112416%29+%29%29&view=COMPLETE&httpAccept=application/xml&apiKey=7f592e39046a1428efc18dbf075455fc')
def output_from_URL(URL = 'valid url not defined yet', encodingFormat = defaultEncodingFormat, reprocessTag = 'N'):
	file_problem_URL_ARRAY = 'error_file_problem_URL_ARRAY'
	file_problem_URL_ARRAY2 = 'error_file_problem_URL_ARRAY2'
	try:
		URL_output = 'Invalid output unless replaced after Exceptions handling'
		#print(URL_output)
		if URL == "valid url not defined yet": ## a valid URL was not returned for some reason, so flag an error state.
			pass #print("An invalid URL or EMPTY SET was returned. There will be error!!!")
		else:
			response = urllib.request.urlopen(URL) ## Open the webpage
			data = response.read() ## Read the webpage
			response.close() ## Close the webpage
			
			global API_KEY_USAGE ## specifying the GLOBAL VARIABLE
			API_KEY_USAGE = API_KEY_USAGE + 1 ## incrementing the GLOBAL VARIABLE by 1 (this is right after the actual web-based query is executed)
			print("API_KEY_USAGE: "+str(API_KEY_USAGE))
			
			URL_output = data.decode(encodingFormat) ## Decode the data into a text readable format
			
	except urllib.error.HTTPError as err: ## HTTP exception
		now = datetime.datetime.now()
		if reprocessTag == 'Y':
			write_to_file(file_problem_URL_ARRAY2, URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
			problem_URL_ARRAY2.append(URL) ## stores the URL with mismatched tags.
		else:
			write_to_file(file_problem_URL_ARRAY, URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
			#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags.
			
		if err.code == 404:
			print(' - '+now.strftime("%H:%M:%S")+" - ERROR 404: INVALID EID or query")
			filename = "EID_E404_invalid_queries.txt"
			stringToWrite = ' - '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
		elif err.code == 400:
			print(' - '+now.strftime("%H:%M:%S")+" - ERROR: EXCEEDED MAX NUMBER ALLOWED FOR THE SERVICE LEVEL")
			filename = "EID_E400_error_file_maximum_request_exceeded.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
		elif err.code == 500:
			print(' - '+now.strftime("%H:%M:%S")+" - SYSTEM_ERROR: A failure has occurred within Scopus")
			filename = "EID_E500_error_file_back-end_processing_error.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(10) ## give more time here for Scopus system to recover
			
		else:
			print(' - '+now.strftime("%H:%M:%S")+" - HTTP ERROR: UNSURE OF CAUSE")
			filename = "EID_other_error_file.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
	except: ## non-HTTP exception
		now = datetime.datetime.now()
		print(' - '+now.strftime("%H:%M:%S")+" - ERROR: NON HTTP UNSURE OF CAUSE")
		error_txt = 'ERROR_non_http'
		
		if reprocessTag == 'Y':
			write_to_file(file_problem_URL_ARRAY2, URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
			problem_URL_ARRAY2.append(URL) ## stores the URL with mismatched tags.
			
		else:
			write_to_file(file_problem_URL_ARRAY, URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
			#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags.
			
		filename = "EID_another_error_file_non_http_other_errors.txt"
		stringToWrite = ' - '+str(error_txt)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
		write_to_file(filename,stringToWrite)
		time.sleep(5)
		
	totalResultsStartTag = START_END_TAGS_ARRAY[0][0]
	totalResultsEndTag = START_END_TAGS_ARRAY[0][1]
	queryID = START_END_TAGS_ARRAY[0][2]
	#print("here1")
	totalResults_array = extract_xml_data(queryID,URL,URL_output,totalResultsStartTag,totalResultsEndTag,description='') ## a 1-element array for the size of result set (can be 0-25)
	print("len(totalResults_array) is "+str(len(totalResults_array)))
	
	if len(totalResults_array) >= 1: ## there is at least ONE valid EID with data (in fact, this value should ONLY BE ONE)
		totalResults_array[0] = int(totalResults_array[0]) ## NOTE, totalResults_array[0] IS A STRING when harvested from the URL_output. 
		if totalResults_array[0] == 0: ## Result set is empty
			URL_output = 'Invalid output unless replaced after Exceptions handling'
			
		print("totalResults_array[0] = "+str(totalResults_array[0]))
		
	else:
		print("no totalResults_array returned: empty result")
		URL_output = 'Invalid output unless replaced after Exceptions handling'
		
	#print("here3")
	return URL_output;

def validatedArraySize(data_array, queryID, min_error_value, max_error_value = '', function_name = 'function_name_not_provided'):
	now = datetime.datetime.now()
	filename = "EID_data_error_file.txt"
	size_of_data_array = len(data_array)
	if max_error_value != '': ## do the following ONLY if max_error_value has a non-null value as an INTEGER
		max_error_value = int(max_error_value) ## convert the argument to INT (doesn't matter if arg is passed as string or int as long as it is a NUMBER!!!)
		if(size_of_data_array >= max_error_value):
			print("ERROR!!! array_size for queryID "+queryID+" is >= "+str(max_error_value)+": "+str(size_of_data_array)+".\n This must NEVER happen!!!\n")
			stringToWrite = now.strftime("%H:%M:%S")+" - error in "+function_name+"(): array_size for queryID "+queryID+" is >= "+str(max_error_value)+": "+str(size_of_data_array)
			write_to_file(filename,stringToWrite)
			
	if(size_of_data_array <= min_error_value):
		print("ERROR!!! array_size for queryID "+queryID+" is <= "+str(min_error_value)+": "+str(size_of_data_array)+".\n This must NEVER happen!!!\n")
		stringToWrite = now.strftime("%H:%M:%S")+" - error in "+function_name+"(): array_size for queryID "+queryID+" is <= "+str(min_error_value)+": "+str(size_of_data_array)
		write_to_file(filename,stringToWrite)
		
	return size_of_data_array;

####========================================================================================================================================================================================
## NAN modified to process number mismatch issues
## queryID can be processed ScopusID, EID, afID etc., depending on the actual script being run. description describes the queryID's specific tagged-data fields
####========================================================================================================================================================================================
def extract_xml_data(queryID, URL, URL_output, starttag, endtag, description = ''):
	output = [] ## creating an empty array. when valid, it will contain the relevant extracted URL_output. In case of number-mismatch error the invalid output will be ignored by the invoking code
	repition = 0 ## this counter keeps track of repeat runs for the mismatch error check before storing it for re-process
	filename = "EID_extract_xml_data_error_file.txt"
	
	while repition < 6: ## try parsing the data for 5 times before storing the problem/error. Generally, a repeat problem does not happen if the error was RANDOM.
		s = [(m.start(0), m.end(0)) for m in re.finditer(starttag,URL_output)] # Loop through start tags
		e = [(m.start(0), m.end(0)) for m in re.finditer(endtag,URL_output)] # Loop through end tags
		repition = repition + 1 ## increment repition
		
		if len(s)!=len(e): ## tag mismatch occured
			now = datetime.datetime.now()
			print("\nWarning: mismatch in number of XML tags. "+str(len(s))+" "+starttag+" but "+str(len(e))+" "+endtag+". \nRepition: "+str(repition)+". Will try "+str(5-repition)+" more times")
			stringToWrite = now.strftime("%H:%M:%S")+' - '+'queryID: '+queryID+description+"- Warning: mismatch in number of XML tags. "+str(len(s))+" "+starttag+" but "+str(len(e))+" "+endtag+". Repition: "+str(repition)+". Will try "+str(5-repition)+" more times\n"
			write_to_file(filename,stringToWrite)
			
			if repition >= 5:
				if description != '':
					problem_EIDs_ARRAY.append(queryID) ## ONLY append queryID (which will be a EID) if a non-null description is passed to the function
					description = ' (mismatch for: '+description+')'
					
				stringToWrite = now.strftime("%H:%M:%S")+' - '+'FAILED 5 TIMES FOR queryID: '+queryID+description+'\n'
				write_to_file(filename,stringToWrite)
				
				write_to_file('error_file_problem_URL_ARRAY', URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
				#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags.
				output = ['Number mismatch'] ## flags the error
				break ## get out of loop and return the error state. Probably redundant if while loop is executed for < 6 times.
				
			else: ## reset arrays of start and end tag positions for the next iteration
				s[:] = []
				e[:] = []
		else: ## tag mismatch has not been encountered
			x = [(s[i][1],e[i][0]) for i in range(0,len(s))]
			i=0
			while  i < len(x):
				output.append((URL_output[x[i][0]:x[i][1]]))
				i=i+1
				
			break ## get out of loop if no mismatch is encountered and a valid output is present.
			
	return output; ## output is an array containing one or more elements

def convert_multiple_data_array_to_stringList(array, description, queryID):
	string = ''
	arraySize = len(array)
	for i in range(0, arraySize):
		element = array[i]
		element = format_cell_data(description,element,queryID)
		if i < arraySize-1: ## there are more records
			string = string + str(element) + '_||_' ## append the delimiter '_||_' if element is NOT the last entry
		else: ## this is the last record
			string = string + str(element) ## do NOT append the delimiter '_||_' if the element is the last entry
	return string;

def transposeArrayOfArray(arrayOfDataArray):
	transposedArrayOfDataArray = [] ## creating an empty array
	transposedArrayOfDataArray = list(map(list, zip(*arrayOfDataArray)))	
	return transposedArrayOfDataArray;

##==========================================================================================
## DEVELOP THIS FURTHER: 
## depending on description, use different tags (defined here) to extract
## data for:
## 			AFID_List--  one row per AF-ID, AfName, City, Country, Aff_url
##			AuthorsList-- one row per AuthName, AU-ID, AuORCID, AF-ID, Au_url
##			FundingDetails-- one row per fund-sponsor, fund-acr, fund-no
##==========================================================================================
def process_multiple_data_value_list(cell_data_array,queryID,description):
	now = datetime.datetime.now()
	detailed_tag_pair_array = [] ## stores the tag details that are specific to the description passed as argument
	EIDvalue = [queryID] ## stores the EID as the first element of the final (valid) multiple_data_array that will be returned
	multiple_data_array = [] ## this array will store the processed data
	temp_array_of_array = [] ## temporarily store multiple_data_array to obtain transposed element (names/IDs) only
	need_to_process_multiple_data = 'yes' ## detailed_tag_pair_array will be traversed if this is 'yes' (default value)
	#pass  
	
	if description == 'AffiliationList':
		#print("Special description: "+description)
		#header3 = ['EID','AfilliationName','AfilliationID','AfilliationCity','AfilliationCountry','AfilliationURL']
		detailed_tag_pair_array = [
									['<affilname>', '</affilname>', 'AfilliationName'],
									['<afid>', '</afid>', 'AfilliationID'],
									['<affiliation-city>', '</affiliation-city>', 'AfilliationCity'],
									['<affiliation-country>', '</affiliation-country>', 'AfilliationCountry'],
									['<affiliation-url>', '</affiliation-url>', 'AfilliationURL']
								]
		#multiple_data_array = cell_data_array ## returns the supplied cell_data_array for now
		#pass
		
	elif description == 'AuthorList':
		#print("Special description: "+description)
		#header4 = ['EID','AuthName','AuthorID','AuthORCID','AuthorAffIDList','AuthorURL']
		detailed_tag_pair_array = [
									['<authname>', '</authname>', 'AuthName'],
									['<authid>', '</authid>', 'AuthorID'],
									['<orcid>', '</orcid>', 'AuthORCID'],
									['<afid>', '</afid>', 'AuthorAffIDList'],
									['<author-url>', '</author-url>', 'AuthorURL']
								]
		#multiple_data_array = cell_data_array ## returns the supplied cell_data_array for now
		#pass
		
	# elif description == 'FunderSponsorList':
		# #print("Special description: "+description)
		# #header5 = ['EID','FundingAgencyName','FundingID','FundingAgencyAcronym']
		# detailed_tag_pair_array = [
									# ['<fund-sponsor>', '</fund-sponsor>', 'FundingAgencyName'],
									# ['<fund-no>', '</fund-no>', 'FundingID'],
									# ['<fund-acr>', '</fund-acr>', 'FundingAgencyAcronym']
								# ]
		# #multiple_data_array = cell_data_array ## returns the supplied cell_data_array for now
		# #pass
		
	else:
		print("ERROR: "+description+" has multiple values")
		filename = "EID_data_error_file.txt"
		stringToWrite = now.strftime("%H:%M:%S")+' - * - '+description+" for EID "+str(queryID)+" has multiple values.\n"
		write_to_file(filename,stringToWrite)
		multiple_data_array = cell_data_array ## returns the supplied cell_data_array as no detailed_tag_pair_array are relevant 
		
		need_to_process_multiple_data = 'no' ## detailed_tag_pair_array will NOT be traversed
		
	if need_to_process_multiple_data == 'yes':
		startIndex = 0
		endIndex = len(detailed_tag_pair_array)
		for cell_data in cell_data_array:
			URL = 'within process_multiple_data_value_list(); EID='+queryID+',recursion_enabled=no'
			remaining_row_data_array = harvest_remaining_cell_data(startIndex,endIndex,queryID,URL,cell_data,detailed_tag_pair_array,recursion_enabled='no') ## returns the remaining data
			
			if remaining_row_data_array[0] == -1:
				print("harvest_remaining_cell_data() returned illegal/error value for EID: "+queryID)
				multiple_data_array = [-1]
				multiple_data_array.append(queryID)
				
			else: ## everything worked normally
				multiple_data_array = EIDvalue + remaining_row_data_array ## combines the first data (EID) with its respective remaining data
				temp_array_of_array.append(multiple_data_array)
				
				## the following appends multiple_data_array to the respective global EID_***_ARRAYS for final printing in the end
				if description == 'AffiliationList':
					EID_AFILLIATIONS_ARRAY.append(multiple_data_array)
				elif description == 'AuthorList':
					EID_AUTHORS_ARRAY.append(multiple_data_array)
				# elif description == 'FunderSponsorList':
					# EID_FUNDERS_ARRAY.append(multiple_data_array)				
				else:
					print("The supplied cell_data_array is returned as is \n  since no detailed_tag_pair_array are relevant for "+description)
					
			
		temp_array_of_array = uniquify_Array(temp_array_of_array) ## remove duplicated records
		if len(temp_array_of_array) > 1: ## when there are more than one UNIQUE multiple_data_array appended
			temp_array_of_array = transposeArrayOfArray(temp_array_of_array) ## transposing the array
			multiple_data_array = temp_array_of_array[1] ## the first element is EID, the second element is names/IDs
			
		elif len(temp_array_of_array) <= 0: ## this must NEVER HAPPEN
			print("ERROR: len(temp_array_of_array)<=0 for EID: "+queryID)
			multiple_data_array = [-1]
			multiple_data_array.append(queryID)
			
		else: ## len(temp_array_of_array)==1; the single instance of the SAME multiple_data_array is returned
			#print("len(temp_array_of_array)= "+str(len(temp_array_of_array)))
			single_value = str(temp_array_of_array[0][1]) ## second element of the first (and ONLY) array of temp_array_of_array is the name/ID 
			multiple_data_array = [single_value]
			
	return multiple_data_array;

def format_cell_data(description, cell_data, queryID):
	now = datetime.datetime.now()
	if description == 'PubISSN' or description == 'Pub_eISSN':
		if len(cell_data) != 8: ## a valid (raw) e/ISSN must ALWAYS be 8 characters (before the hyphen is inserted). typical formatted e/ISSN is 1234-5678
			print("Invalid "+description+" for EID "+str(queryID)+": "+str(cell_data))
			filename = "EID_data_error_file.txt"
			stringToWrite = now.strftime("%H:%M:%S")+' - * - '+"Invalid "+description+" for EID "+str(queryID)+": "+str(cell_data)+".\n"
			write_to_file(filename,stringToWrite)
			
			filename2 = "#EIDs_with_invalid_(e)ISSN"
			stringToWrite = str(queryID)+": "+str(cell_data)
			write_to_file(filename2,stringToWrite)
			
		left_substr = cell_data[:4]
		right_substr = cell_data[4:]
		cell_data = str(left_substr+'-'+right_substr)
		
	# elif description == 'AuthorList' or description == 'AffiliationList' or description == 'FunderSponsorList':
		# #process_multiple_data_value_list(cell_data_array,queryID,description) ##<--------------$$$$$$$$$$ DEVELOP THIS FURTHER
		
	else:
		cell_data = str(cell_data)
		
	return cell_data;

def harvest_remaining_cell_data(startIndex, endIndex, queryID, URL, data, suppliedTagPairArray = '', recursion_enabled = 'no'): ## data is the (long) text entry/URL_output
	remaining_row_data_array = []
	if suppliedTagPairArray == '':
		suppliedTagPairArray = START_END_TAGS_ARRAY
		
	for j in range(startIndex,endIndex):
		tag_pair_array = suppliedTagPairArray[j]
		starttag = tag_pair_array[0]
		endtag = tag_pair_array[1]
		description = tag_pair_array[2]
		
		cell_data_array = extract_xml_data(queryID,URL,data,starttag,endtag,description) ## extracting data for non-EID 'DESCRIPTION' field (size can be 0 or more)
		if cell_data_array == ['Number mismatch']: ## XML mismatch occured so assign error state
			print("ERROR: cell_data_array == ['Number mismatch'] for queryID: "+queryID)
			remaining_row_data_array = [-1] ## returns an illegal value to indicate error and ignores all subsequent calculations
			remaining_row_data_array.append(queryID)
			
		else: ## no XML mismatch occured for non-EID data so proceed with further extraction; NOTE, MIN size of cell_data_arra is 0 and there are no MAX limit
			size_of_cell_data_array = validatedArraySize(cell_data_array,queryID,min_error_value=-1,max_error_value='',function_name='harvest_remaining_cell_data')
			if size_of_cell_data_array == 0: 
				cell_data = str('no_'+description+'_Data')
				if description == 'AuthorList':
					filename = "#EIDs_with_no_"+description
					stringToWrite = str(queryID)
					write_to_file(filename,stringToWrite)
					
				if description == 'AffiliationList':
					filename = "#EIDs_with_no_"+description
					stringToWrite = str(queryID)
					write_to_file(filename,stringToWrite)
				
			elif size_of_cell_data_array == 1 and description != 'AffiliationList' and description != 'AuthorList': #and description != 'FunderSponsorList': 
				cell_data = str(cell_data_array[0])
				cell_data = format_cell_data(description,cell_data,queryID) ## this should potentially be at the end of the else clause before remaining_row_data.append(cell_data)
				
			elif size_of_cell_data_array > 1 or description == 'AffiliationList' or description == 'AuthorList': #or description == 'FunderSponsorList':
				if recursion_enabled == 'yes':
					multiple_data_array = process_multiple_data_value_list(cell_data_array,queryID,description) ##<--------------$$$$$$$$$$ DEVELOP THIS FURTHER
					if multiple_data_array[0] == -1:
						print("process_multiple_data_value_list() returned illegal/error value for EID: "+queryID)
						remaining_row_data_array = [-1] ## returns an illegal value to indicate error and ignores all subsequent calculations
						remaining_row_data_array.append(queryID)
						
					else:
						cell_data = convert_multiple_data_array_to_stringList(multiple_data_array,description,queryID)
						
				else: ## recursion is DISABLED
					cell_data = convert_multiple_data_array_to_stringList(cell_data_array,description,queryID)
					
			else: ## size_of_cell_data_array can't be -ve EVER!!!
				print("ERROR!!! size_of_cell_data_array is less than zero: "+str(size_of_cell_data_array)) 
				cell_data = str('ERROR: -veArraySize for_'+description)
				
			#cell_data = format_cell_data(description,cell_data,queryID) ## this should potentially be at the end of the else clause before remaining_row_data.append(cell_data)
			remaining_row_data_array.append(cell_data) ## this is here to ensure data is appended ONLY if no XML mismatch occured for non-EID field(s)
						
	return remaining_row_data_array;

def create_EID_data_Array_of_array(URL, URL_output, totalProcessedEIDs):	
	#now = datetime.datetime.now()
	
	ErrorStatus = 'No Errors So Far...' ## this is a flag for which the value of -1 indicates an error state; after successful execution it indicates number of EIDs processed successfuly. 
	#EID_row_data_array = [] ## defining an array to contain each row of data for a given EID
	EID_data_Array_of_array = [] ## creating an empty array of array that will hold all the successfully processed EID_row_data_array
	
	entryStartTag = START_END_TAGS_ARRAY[1][0]
	entryEndTag = START_END_TAGS_ARRAY[1][1]
	entryDescription = START_END_TAGS_ARRAY[1][2]
	startEIDrange = totalProcessedEIDs+1 ## +1 reflects the more 'intuitive' count
	endEIDrange = totalProcessedEIDs+defaultItemsPerPage ## +defaultItemsPerPage reflects the more 'intuitive' count
	queryID = entryDescription+str(startEIDrange)+'-'+str(endEIDrange) ## e.g. the first batch will be PubEntries1-25
	
	print("\nProcessing Entry_object_array: "+queryID)
	Entry_object_array = extract_xml_data(queryID,URL,URL_output,entryStartTag,entryEndTag,description='') ## an array of EID entries (size can be 0 to 25)
	if Entry_object_array == ['Number mismatch']: ## XML mismatch occured so assign error state
		print("ERROR: Entry_object_array == ['Number mismatch'] for queryID: "+queryID)
		ErrorStatus = -1 ## returns an illegal value to indicate error and ignores all subsequent calculations
		EID_data_Array_of_array = [-1]
		EID_data_Array_of_array.append(queryID)
		
	else: ## no XML mismatch occured for Entry_object_array so proceed with further extraction
		size_of_Entry_object_array = validatedArraySize(Entry_object_array,queryID,min_error_value=0,max_error_value=26,function_name='create_EID_data_Array_of_array')
		if size_of_Entry_object_array <= 0 or size_of_Entry_object_array >= 26: ## this should NEVER happen
			print("ERROR: size_of_Entry_object_array <= 0 or size_of_Entry_object_array >= 26 for queryID: "+queryID)
			ErrorStatus = -1
			EID_data_Array_of_array = [-1]
			EID_data_Array_of_array.append(queryID)
			
		else: ## do the following ONLY if there are up to 1-25 records (inclusive). The max limit CAN be less than 25 for the 'remainder' entries
			print("  EID entries extracted: "+str(size_of_Entry_object_array)+" of (maximum) "+str(defaultItemsPerPage)+" supllied EIDs")
			EIDstartTag = START_END_TAGS_ARRAY[2][0] ## specifically extracting from START_END_TAGS_ARRAY[2] (= EID tags)
			EIDendTag = START_END_TAGS_ARRAY[2][1] ## specifically extracting from START_END_TAGS_ARRAY[2] (= EID tags)
			#EIDdescription = START_END_TAGS_ARRAY[1][2] ## specifically extracting from START_END_TAGS_ARRAY[2] (= EID tags)
			
			for i in range(0,size_of_Entry_object_array):
				cell_data_array = [] ## defining a temporary array to contain each data field for a given EID
				Entry_object = Entry_object_array[i] ## a single-element array containing tagged-data to be placed in multiple columns is copied; Entry_object is just a (long) text entry
				queryID = 'Extracting_EID'+str(i+startEIDrange) ## +startEIDrange reflects the more 'intuitive' count e.g. 'Extracting_EID1' for the first entry (i=0)
				
				cell_data_array = extract_xml_data(queryID,URL,Entry_object,EIDstartTag,EIDendTag,description='') ## extracting the PubEID; SIZE MUST ONLY BE ONE element
				if cell_data_array == ['Number mismatch']: ## XML mismatch occured so assign error state
					print("ERROR: cell_data_array == ['Number mismatch'] for queryID: "+queryID)
					ErrorStatus = -1 ## returns an illegal value to indicate error and ignores all subsequent calculations
					EID_data_Array_of_array = [-1]
					EID_data_Array_of_array.append(queryID)
					
				else: ## no XML mismatch occured for EID so proceed with further extraction
					size_of_cell_data_array = validatedArraySize(cell_data_array,queryID,min_error_value=0,max_error_value=2,function_name='create_EID_data_Array_of_array')
					if size_of_cell_data_array != 1: ## SIZE MUST ONLY BE ONE: one EID per entry
						print("size_of_cell_data_array for "+queryID+" is not 1: "+str(size_of_cell_data_array))
						ErrorStatus = -1
						EID_data_Array_of_array = [-1]
						EID_data_Array_of_array.append(queryID)
						
					else: ## do this because there is one EID per entry
						EID_row_data_array = [] ## defining an array to contain each row of data for a given EID
						queryID  = cell_data_array[0] ## this is the EID, and must be the the ONLY entry in the single-element array
						EIDvalue = [queryID] ## EID is the first value to be added to EID_row_data_array
						#print("\nProcessing EID: "+queryID)
						
						startIndex = 3  ## starting at 3 because index 0 is for totalResults, 1 for Entry_object, and 2 is for EID - all already used above
						endIndex = len(START_END_TAGS_ARRAY)
						
						remaining_row_data_array = harvest_remaining_cell_data(startIndex,endIndex,queryID,URL,Entry_object,suppliedTagPairArray='',recursion_enabled='yes') ## returns the remaining data
						if remaining_row_data_array[0] == -1:
							print("harvest_remaining_cell_data() returned illegal/error value for EID: "+queryID)
							ErrorStatus = -1
							EID_data_Array_of_array = [-1]
							EID_data_Array_of_array.append(queryID)
							
						else:
							EID_row_data_array = EIDvalue + remaining_row_data_array ## combines the first data (EID) with its respective remaining data
							
							len_EID_row_data_array = validatedArraySize(EID_row_data_array,queryID,min_error_value=(len(HEADER)-1),max_error_value=(len(HEADER)+1),function_name='create_EID_data_Array_of_array')
							if len_EID_row_data_array != len(HEADER): ## check that the number of data_fields match the number of columns
								print("len_EID_row_data_array ("+str(len_EID_row_data_array)+") != len(HEADER) ("+str(len(HEADER))+") for EID: "+queryID)
								ErrorStatus = -1
								EID_data_Array_of_array = [-1]
								EID_data_Array_of_array.append(queryID)
								
							else:
								#print("len_EID_row_data_array ("+str(len_EID_row_data_array)+") is same as len(HEADER) ("+str(len(HEADER))+").\nSuccessfully harvested all records for EID: "+queryID)
								EID_data_Array_of_array.append(EID_row_data_array) ## this is here to ensure EID_row_data_array is appended ONLY if there is a FULL row_data harvest)
							
	print("\n\nErrorStatus at the end of parsing Entry_object_array is: "+str(ErrorStatus))
			
	if len(EID_data_Array_of_array) == 0: ## for some reason if no data were added to EID_data_Array_of_array
		ErrorStatus = -1
		EID_data_Array_of_array = [-1]
		queryID = 'unknown queryID(no data were added to EID_data_Array_of_array)'
		EID_data_Array_of_array.append(queryID)
		
	if ErrorStatus == -1: ## Errors have been encountered due to exceptions raised during extract_xml_data()
		#EID_data_Array_of_array = ErrorStatus ## a negative value of -1 (from ScopusIDs) flags problem/error
		print("XML mismatches or other errors encountered in create_EID_data_Array_of_array(). \n\tSkipping this entry and moving to next item (if exists)...")
		
	else: ## EVERYTHING WORKED NORMALLY...
		ErrorStatus = len(EID_data_Array_of_array) ## should be a non-negative number if all worked normally
		print("\nSuccessfully processed "+str(ErrorStatus)+" of "+str(size_of_Entry_object_array)+" LEGAL EID entries.\n")
		
	return EID_data_Array_of_array; ## this is either an array of arrays, or a single integer value of -1 indicating error state.

## This function loops through and writes scopusIDs and other data in blocks of 25. Also returns the number of processed EIDcount and prints APIkey usage
def process_EID_data(csvwriter, EID_List_to_Process, argumentValues, totalProcessedEIDs, suppliedURL = '', reprocessTag = 'N'): ## reprocessTag = 'N' (no; default) or 'Y' (yes)
	#now = datetime.datetime.now()
	apiKey  = argumentValues[0]
	encodingFormat = argumentValues[1]
	EID_data_Array_of_array = [] ## EID_data_Array_of_array should be EITHER a correctly structred array of row_data_array with all data ready to be written to csv file OR -1 indicating an error state
	newEIDcount = 0 ## this counts only the new EIDs being harvested (compare that to totalProcessedEIDs which counts the ENTIRE EIDs being harvested so far)
	
	if suppliedURL == '': ## EID_List_to_Process is EMPTY when suppliedURL is NOT NULL
		URL = generate_EID_URL(EID_List_to_Process,reprocessTag,apiKey)
	else:
		URL = suppliedURL ## EID_List_to_Process is EMPTY when suppliedURL is NOT NULL
		
	URL_output = output_from_URL(URL,encodingFormat,reprocessTag)
	if URL_output == 'Invalid output unless replaced after Exceptions handling': ## somehow an illegal URL_output has been passed
		EID_data_Array_of_array = [-1] ## this is the default error state unless replaced after successful extract_xml_data()
		reason = 'Invalid URL output'
		EID_data_Array_of_array.append(reason)
		
	else:
		EID_data_Array_of_array = create_EID_data_Array_of_array(URL,URL_output,totalProcessedEIDs)
			
	if EID_data_Array_of_array[0] == -1: ## invalid/error state from validation, most likely due to mismatch in XML tags
		reason_queryID = EID_data_Array_of_array[1] ## if EID_data_Array_of_array[0] == -1, a reason or queryID is ALWAYS appended (and length is ALWAYS 2)
		print("Illegal state of data (EID_data_Array_of_array[0] == -1).\n Reason/queryID: "+reason_queryID+". len(EID_data_Array_of_array)= "+str(len(EID_data_Array_of_array))+".\n\tSkipping this and moving to next item (if exists)...")
		now = datetime.datetime.now()
		filename = "EID_data_error_file.txt"
		stringToWrite = now.strftime("%H:%M:%S")+' - '+reprocessTag+' - '+"Illegal state of data (EID_data_Array_of_array[0] == -1). Reason/queryID: "+reason_queryID+". len(EID_data_Array_of_array)= "+str(len(EID_data_Array_of_array))+".\n"
		write_to_file(filename,stringToWrite)
		
		if reprocessTag == 'Y':
			write_to_file('error_file_problem_URL_ARRAY2', URL) ## writes the URL with mismatched tags (may have been caused from one or more EIDs)
			problem_URL_ARRAY2.append(URL)
			
	else: ## a valid EID_data_Array_of_array has been obtained, write to CSV
		print("	Writing data to file...\n")
		
		## an inner loop here to write the records to the CSV. DO THIS ONLY IF NO EXCEPTIONS ARE RAISED AND ALL DATA IS AVAILABLE TO BE WRITTEN IN BLOCKS OF 200
		for i in range(0,len(EID_data_Array_of_array)):
			processedData_array = EID_data_Array_of_array[i]
			EID = processedData_array[0] ## the EID is *always* the first element of the array
			write_data_to_CSV(csvwriter,processedData_array)
			DATA_WRITTEN_TO_CSV.append(processedData_array)
			newEIDcount = newEIDcount + 1
			totalProcessedEIDs = totalProcessedEIDs + 1 ## this line is unnecessary if the following print() is commented out
			#print("\twriting EID record: "+str(totalProcessedEIDs))
					
			if reprocessTag == 'Y':
				successful_EIDs_ARRAY2.append(EID)
				write_to_file('successful_URL_ARRAY2', URL) ## writes the successfully processed URL
				#successful_URL_ARRAY2.append(URL)
				
			else: ##reprocessTag == 'N', ie, the first pass
				successful_EIDs_ARRAY.append(EID)
				write_to_file('successful_URL_ARRAY', URL) ## writes the successfully processed URL
				#successful_URL_ARRAY.append(URL)	
				
			global EID_COUNTER
			EID_COUNTER = EID_COUNTER + 1
			
	print("\nEID count= "+str(EID_COUNTER)+" of "+str(EIDS_IN_FILE)+" EIDs in File. APIkey used "+str(API_KEY_USAGE)+" times.")
	
	return newEIDcount;

def iterate_through_EID_list_file_and_write_data(argumentValues, csvwriter, supplied_EID_List, reprocessTag = 'N', suppliedURL = ''): ## reprocessTag = 'N' (no; default) or 'Y' (yes)
	maxEIDs_toProcess = defaultItemsPerPage	
	reprocess_description = 'Reprocessing problem_EIDs_ARRAY:\n'
	## an outer loop here to go through a list of EIDs for which to search for and retrieve relevant data
	#print("	Entering loop...")
	
	if reprocessTag == 'N': ## if NOT re-processing problem EIDs, then supplied_EID_List is the original EID_LIST, else supplied_EID_List is the unique_problem_EIDs_ARRAY
		supplied_EID_List = EID_LIST ## else supplied_EID_List is the problem_EIDs_ARRAY
		reprocess_description = ''
		
	len_supplied_EID_List = validatedArraySize(supplied_EID_List,queryID='supplied_EID_List',min_error_value=0
												,max_error_value='',function_name='iterate_through_EID_list_file_and_write_data') ## note, max value CAN be more than 25 if reprocessTag = 'N'
	
	number_of_iterations = int(len_supplied_EID_List/maxEIDs_toProcess)+1 ## one ADDITIONAL cycle to take care of the 'remainder'
	print(reprocess_description+"URLs need to be created "+str(number_of_iterations)+" time(s) when maxEIDs_toProcess = "+str(maxEIDs_toProcess))
	
	startSpliceIndex = 0
	endSpliceIndex = maxEIDs_toProcess
	totalProcessedEIDs = 0
	for itr in range(0,number_of_iterations):
		EID_List_to_Process = supplied_EID_List[startSpliceIndex:endSpliceIndex]
		newEIDs = process_EID_data(csvwriter,EID_List_to_Process,argumentValues,totalProcessedEIDs,suppliedURL,reprocessTag)
		
		startSpliceIndex = startSpliceIndex + maxEIDs_toProcess
		endSpliceIndex = endSpliceIndex + maxEIDs_toProcess
		totalProcessedEIDs = totalProcessedEIDs + newEIDs
		if totalProcessedEIDs >= len_supplied_EID_List:
			#print("\nSUCCESSFULLY HARVESTED ALL "+str(totalProcessedEIDs)+" ENTRIES OF TOTAL "+str(len_supplied_EID_List)+" EIDs.") ## this is commented because at the end of the iteration, totalProcessedEIDs MAY STILL BE LESS than len_supplied_EID_List if EID_LIST had illegal entries
			break
			
		else:
			print("Have more records to harvest. Increasing count by "+str(maxEIDs_toProcess)+" and restarting")
			
	if reprocessTag == 'N':
		print("\nDATA HARVEST COMPLETED FOR "+str(totalProcessedEIDs)+" *LEGAL* ENTRIES OF TOTAL "+str(len_supplied_EID_List)+" EIDs.") ## at the end of the iteration, all records are harvested
	#EIDcount = EID_COUNTER ## this is most probably redundant: EID_COUNTER can do the same job
	return totalProcessedEIDs;

def print_and_write_ArrayDataContents(ARRAY, arrayName = "no_name array", toPrint = 0, toWrite = 1): ## toPrint and toWrite can be either 1 (do action) or another number, typically 0 (no action)
	print("\nPrinting/Writing contents of array: "+arrayName)
	file_name = str(len(ARRAY))+"_"+str(arrayName)+".txt"
	
	for element in ARRAY:
		if type(element) == list:
			#print("element type is list/array. Converting to string.")
			element = str(element) ## convert the list/array into string so it can be written to file. The output may not be very useful.
			
		if toPrint == 1: print(element)
		if toWrite == 1: write_to_file(file_name,element)
		
	return;

####========================================================================================================================================================================================
## Note that this function is comprised of if statements that really work as CASE clauses. There are repetitions in code, but that is 
## unavoidable because depending on what processFlagCount is passed, the code run is exclusive
####========================================================================================================================================================================================
def write_final_summary_EIDs_File(processFlagCount): ## <---------$$$$$$$$$$$ Need to create/modify code here
	filename = "#final_summary_EIDs.txt"
	
	print("\nData write"+str(processFlagCount)+" complete.\n  Processed "+str(EID_COUNTER)+" EIDs (file had "+str(EIDS_IN_FILE)+" entries). ")
	
	stringToWrite = "\nData write"+str(processFlagCount)+" complete.\n\tProcessed "+str(EID_COUNTER)+" EIDs (file had "+str(EIDS_IN_FILE)+" entries)"
	write_to_file(filename,stringToWrite)
	global problem_EIDs_ARRAY ## specifying the GLOBAL VARIABLE (needed for adding missedEIDs[] below)
	missedEIDs = [] ## an array to store EIDs that were missed during data harvest; this is most likely due to illegal EID without any Scopus data
	for EID in EID_LIST:
		if ((EID != 'Trying to re-process problem EIDs (if any)') ## ignore "Trying to re-process problem EIDs" text
			and (EID not in problem_EIDs_ARRAY) and (EID not in successful_EIDs_ARRAY)): ## if EID is missing in BOTH successful_EIDs_ARRAY and problem_EIDs_ARRAY
			#print("\tEID missing in BOTH successful_ and problem_EIDs_ARRAY:\n "+str(EID)) ## mute this: too much text!!!
			missedEIDs.append(EID)
			
	if processFlagCount == 1: ## general, first-pass data write
		if EID_COUNTER > 0: ## the following will ONLY happen if there is AT LEAST ONE EID successfully harvested.
			print("\nThere are "+str(len(successful_EIDs_ARRAY))+" records in successful_EIDs_ARRAY.")
			print("\nThere are "+str(len(problem_EIDs_ARRAY))+" records in problem_EIDs_ARRAY!!!\n")
			
			stringToWrite = "\nThere are "+str(len(successful_EIDs_ARRAY))+" records in successful_EIDs_ARRAY"
			write_to_file(filename,stringToWrite)			
			stringToWrite = "There are "+str(len(problem_EIDs_ARRAY))+" records in problem_EIDs_ARRAY!!!\n"
			write_to_file(filename,stringToWrite)
			
			if(len(missedEIDs) > 0):
				print("There are "+str(len(missedEIDs))+" EID(s) missing in BOTH successful_EIDs_ARRAY and problem_EIDs_ARRAY that are in EID_LIST!!!")
				print("These will be added to problem_EIDs_ARRAY")
				
				stringToWrite = "There are "+str(len(missedEIDs))+" EID(s) missing in BOTH successful_EIDs_ARRAY and problem_EIDs_ARRAY that are in EID_LIST!!!\n\tThese will be added to problem_EIDs_ARRAY\n"
				write_to_file(filename,stringToWrite)
				
				#global problem_EIDs_ARRAY ## specifying the GLOBAL VARIABLE (needed for adding missedEIDs[])
				problem_EIDs_ARRAY = problem_EIDs_ARRAY + missedEIDs
				
	elif processFlagCount == 2: ## second-pass data write if pEID_array has records
		print("\nTried to reprocess "+str(len(problem_EIDs_ARRAY))+" records in problem_EIDs_ARRAY.\n")
		print("\n\tThere were "+str(len(unique_problem_EIDs_ARRAY))+" UNIQUE records in unique_problem_EIDs_ARRAY.\n")
		#print("\nThere were "+str(len(unique_successful_EIDs_ARRAY))+" records in unique_successful_EIDs_ARRAY.\n")
		
		stringToWrite = "\nThere were "+str(len(successful_EIDs_ARRAY))+" records in successful_EIDs_ARRAY ("+str(len(unique_successful_EIDs_ARRAY))+" were UNIQUE records)." ## -1 to ignore "Trying to re-process problem EIDs" text (THIS HAS BEEN MUTED NOW)
		write_to_file(filename,stringToWrite)		
		stringToWrite = "\nTried to REPROCESS the "+str(len(problem_EIDs_ARRAY))+" records in problem_EIDs_ARRAY ("+str(len(unique_problem_EIDs_ARRAY))+" were UNIQUE records)." ## -1 to ignore "Trying to re-process problem EIDs" text (THIS HAS BEEN MUTED NOW)
		write_to_file(filename,stringToWrite)
		stringToWrite = "\nThere are now "+str(len(successful_EIDs_ARRAY2))+" recovered records in successful_EIDs_ARRAY2 ("+str(len(unique_successful_EIDs_ARRAY2))+" are UNIQUE records)."
		write_to_file(filename,stringToWrite)
		
		for EID in EID_LIST:
			if ((EID != 'Trying to re-process problem EIDs (if any)') ## ignore "Trying to re-process problem EIDs" text
				and (EID not in successful_EIDs_ARRAY2) and (EID not in successful_EIDs_ARRAY)): ## if EID is missing in BOTH successful_EIDs_ARRAYs
				#print("EID left unprocessed after re-processing: "+str(EID)) ## muted because too texty
				problem_EIDs_ARRAY2.append(EID)
				
		global unique_problem_EIDs_ARRAY2
		unique_problem_EIDs_ARRAY2 = uniquify_Array(problem_EIDs_ARRAY2)
				
		if (len(unique_problem_EIDs_ARRAY2) > 0):
			print("Data could not be harvested for "+str(len(unique_problem_EIDs_ARRAY2))+" unique EIDs")
			print("These EIDs will be written.")
			stringToWrite = "\nThere are "+str(len(problem_EIDs_ARRAY2))+" illegal(?) EIDs in problem_EIDs_ARRAY2 ("+str(len(unique_problem_EIDs_ARRAY2))+" are UNIQUE records).\n"
			write_to_file(filename,stringToWrite)
			
			print_and_write_ArrayDataContents(problem_EIDs_ARRAY2,'problem_EIDs_ARRAY2',toPrint=0,toWrite=1)
			print_and_write_ArrayDataContents(unique_problem_EIDs_ARRAY2,'#unique_problem_EIDs_ARRAY2',toPrint=0,toWrite=1)
			
		else:
			print("All "+str(len(EID_LIST))+" EID data have been successfully harvested!!!")
			stringToWrite = "\nAll "+str(len(EID_LIST))+" EID data have been successfully harvested!!!\n"
			write_to_file(filename,stringToWrite)
			
		if (len(missedEIDs) > 0):
			print("There are "+str(len(missedEIDs))+" NEW EID(s) missing in BOTH successful_EIDs_ARRAY and problem_EIDs_ARRAY that are in EID_LIST!!!")
			print("This should NOT happen. Contents of this array will be written.")
			
			stringToWrite = "\nThere are "+str(len(missedEIDs))+" NEW EID(s) missing in BOTH successful_EIDs_ARRAY and problem_EIDs_ARRAY that are in EID_LIST!!!\n\tThis should NOT happen. Contents of this array will be written\n"
			write_to_file(filename,stringToWrite)
			print_and_write_ArrayDataContents(missedEIDs,arrayName="missedEIDs",toPrint=0,toWrite=1)
			
		stringToWrite = "\nThere were "+str(len(UNIQUE_DATA_WRITTEN_TO_CSV))+" UNIQUE records written to DATA_WRITTEN_TO_CSV file ("+str(len(DATA_WRITTEN_TO_CSV))+" were non-unique records)."
		write_to_file(filename,stringToWrite)
		
	else: ## processFlagCount is neither 1 nor 2 - THIS MUST NOT HAPPEN!!!
		print("Illegal processFlagCount encountered: "+str(processFlagCount))
		
		stringToWrite = "\n\nIllegal processFlagCount encountered: "+str(processFlagCount)
		write_to_file(filename,stringToWrite)
		
	return;

## This function is authored by Naga. The function uses dataframe from padas package to do the 'flattening'.
## The function expects '#EID_AUTHORS_wAFIDstring.csv' file to be created upstream before this function is invoked
def flatten_EID_AUTHORS_file():
    df = pd.read_csv('#EID_AUTHORS_wAFIDstring.csv')
    
    idx = df['AuthorAffIDList'].str.contains('_')==False
    df2=df[idx]
    #print(df2)
    idx = df['AuthorAffIDList'].str.contains('_')
    df1=df[idx]
    
    idx = df['AuthorAffIDList'].str.contains('no_AuthorAffIDList_Data')
    df5=df[idx]
    
    
    aff=[]
    out=[]
    outlst=[]
    count=1
    for index, row in df1.iterrows():
        
        count=count+1
        
        EID = row['EID']
        Autnam = row['AuthName']
        Authid = row['AuthorID']
        Authorc = row['AuthORCID']
        Affid = row['AuthorAffIDList']
        url = row['AuthorURL']
        aff=Affid.split('_||_')
        for i in aff:
            affid= i
            out= EID,Autnam,Authid,Authorc,affid,url    
            outlst.append(out)
    df4=pd.DataFrame(outlst,columns=['EID', 'AuthName', 'AuthorID', 'AuthORCID', 'AuthorAffIDList','AuthorURL'])
    df2=df2.append(df4)
    df2=df2.append(df5)
    
    flattened_EID_AUTHORS_filename = '##EID_AUTHORS_ARRAY_(flatfile).csv'
    df2.to_csv(flattened_EID_AUTHORS_filename,index=False)        
    return;

## This function writes the EID_***_ARRAY contents to respective files if there are valid contents.
## Also writes the count of items written to "#final_summary_EIDs.txt".
## NOTE, there are repetitions in code. Ideally, want to optimise coding by incorporating a for loop...
def write_EID_OTHERLIST_ARRAY_to_CSV():
	filename = "#final_summary_EIDs.txt"
	
	global EID_AFILLIATIONS_ARRAY
	global EID_AUTHORS_ARRAY
	#global EID_FUNDERS_ARRAY
	
	#EID_AFILLIATIONS_ARRAY = uniquify_Array(EID_AFILLIATIONS_ARRAY)
	#EID_AUTHORS_ARRAY = uniquify_Array(EID_AUTHORS_ARRAY)
	#EID_FUNDERS_ARRAY = uniquify_Array(EID_FUNDERS_ARRAY)
	
	if len(EID_AFILLIATIONS_ARRAY) > 0:
		header3 = ['EID','AfilliationName','AfilliationID','AfilliationCity','AfilliationCountry','AfilliationURL']
		#print_and_write_ArrayDataContents(EID_AFILLIATIONS_ARRAY,'EID_AFILLIATIONS_ARRAY',toPrint=0,toWrite=1)
		EID_AFILLIATIONS_ARRAY = uniquify_Array(EID_AFILLIATIONS_ARRAY)
		
		with open('##EID_AFILLIATIONS.csv', 'w', newline='',encoding='utf-8') as csvfile3: ## Open the csv file------------------1
			csvwriter3 = csv.writer(csvfile3, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
			write_data_to_CSV(csvwriter3,header3) ##write HEADER ONCE
			print("\nWriting csvfile3: EID_AFILLIATIONS_ARRAY...")
			for i in range(0,len(EID_AFILLIATIONS_ARRAY)):
				processedData_array3 = EID_AFILLIATIONS_ARRAY[i]
				write_data_to_CSV(csvwriter3,processedData_array3)
			print("\nFinished writing csvfile3: EID_AFILLIATIONS_ARRAY")
			csvfile3.close() ## Close csv-------------------------4
			
		stringToWrite = "\nThere were "+str(len(EID_AFILLIATIONS_ARRAY))+" records written to EID_AFILLIATIONS_ARRAY file."
		write_to_file(filename,stringToWrite)
		
	if len(EID_AUTHORS_ARRAY) > 0:
		header4 = ['EID','AuthName','AuthorID','AuthORCID','AuthorAffIDList','AuthorURL']
		#print_and_write_ArrayDataContents(EID_AUTHORS_ARRAY,'EID_AUTHORS_ARRAY',toPrint=0,toWrite=1)
		EID_AUTHORS_ARRAY = uniquify_Array(EID_AUTHORS_ARRAY)
		
		with open('#EID_AUTHORS_wAFIDstring.csv', 'w', newline='',encoding='utf-8') as csvfile4: ## Open the csv file------------------1
			csvwriter4 = csv.writer(csvfile4, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
			write_data_to_CSV(csvwriter4,header4) ##write HEADER ONCE
			print("\nWriting csvfile4: EID_AUTHORS_ARRAY...")
			for i in range(0,len(EID_AUTHORS_ARRAY)):
				processedData_array4 = EID_AUTHORS_ARRAY[i]
				write_data_to_CSV(csvwriter4,processedData_array4)
			print("\nFinished writing csvfile4: EID_AUTHORS_file_wAFFIDstring")
			csvfile4.close() ## Close csv-------------------------4
			
			#flattened_EID_AUTHORS_filename = str(len(EID_AUTHORS_ARRAY))+'_EID_AUTHORS_ARRAY_' + time.strftime("%d%m%Y-%H%M") + '.csv'
			flatten_EID_AUTHORS_file()
			print("\nFinished writing flattened_EID_AUTHORS: one row per AFID")
			
		stringToWrite = "There were "+str(len(EID_AUTHORS_ARRAY))+" records written to EID_AUTHORS_ARRAY file."
		write_to_file(filename,stringToWrite)
		
	# if len(EID_FUNDERS_ARRAY) > 0:
		# header5 = ['EID','FundingAgencyName','FundingID','FundingAgencyAcronym']
		# #print_and_write_ArrayDataContents(EID_FUNDERS_ARRAY,'EID_FUNDERS_ARRAY',toPrint=0,toWrite=1)
		# EID_FUNDERS_ARRAY = uniquify_Array(EID_FUNDERS_ARRAY)
		
		# with open(str(len(EID_FUNDERS_ARRAY))+'_EID_FUNDERS_ARRAY_' + time.strftime("%d%m%Y-%H%M") + '.csv', 'w', newline='',encoding='utf-8') as csvfile5: ## Open the csv file------------------1
			# csvwriter5 = csv.writer(csvfile5, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
			# write_data_to_CSV(csvwriter5,header5) ##write HEADER ONCE
			# print("\nWriting csvfile5: EID_FUNDERS_ARRAY...")
			# for i in range(0,len(EID_FUNDERS_ARRAY)):
				# processedData_array5 = EID_FUNDERS_ARRAY[i]
				# #csvwriter2.writerow(processedData_array2[0:len(processedData_array2)]) ## write data while looping-----------------------------------------------------------3b
				# write_data_to_CSV(csvwriter3,processedData_array5)
			# print("\nFinished writing csvfile5: EID_FUNDERS_ARRAY")
			# csvfile5.close() ## Close csv-------------------------4
			
		# stringToWrite = "\nThere were "+str(len(EID_FUNDERS_ARRAY))+" records written to EID_FUNDERS_ARRAY file ("+str(len(EID_FUNDERS_ARRAY))+" were non-unique records)."
		# write_to_file(filename,stringToWrite)
		
	return;

def finalise_validaton_and_logfiles(csvwriter, argumentValues):
	
	file_to_write = "check_processed_records_from_all_EID.txt"
	stringToWrite = "stats BEFORE reprocess:\n Total EIDs processed = "+str(EID_COUNTER)+", Total EIDs in File = "+str(EIDS_IN_FILE)+", Difference = "+str(EIDS_IN_FILE - EID_COUNTER)
	write_to_file(file_to_write,stringToWrite)
	
	processFlagCount = 1 ## typical first-pass data write as long as there are some data written to file (i.e. EID_COUNTER > 0)
	write_final_summary_EIDs_File(processFlagCount)
	
	global unique_problem_EIDs_ARRAY
	unique_problem_EIDs_ARRAY = uniquify_Array(problem_EIDs_ARRAY)
	global unique_successful_EIDs_ARRAY
	unique_successful_EIDs_ARRAY = uniquify_Array(successful_EIDs_ARRAY)
	
	length_of_unique_pEID_array = len(unique_problem_EIDs_ARRAY)
	if length_of_unique_pEID_array > 0: ## do this ONLY if there are problem EIDs stored from various exceptions and mismatch errors
		processFlagCount = 2 ## set processFlagCount to 2 for second-pass data write
		print("\n\nNumber of UNIQUE records in unique_problem_EIDs_ARRAY = "+str(length_of_unique_pEID_array))
		print("------Trying to re-process problem EIDs------\n")
		#problem_EIDs_ARRAY.append("Trying to re-process problem EIDs (if any)") ## this entry might cause an unknown error - just ignore it
		#successful_EIDs_ARRAY.append("Trying to re-process problem EIDs (if any)")
		
		recoveredEIDs = 0 ## reset to zero to reflect recovered EIDs by unique_problem_EIDs_ARRAY
		recoveredEIDs2 = 0 ## reset to zero to reflect recovered EIDs by problem_URL_ARRAY2
		reprocessTag = 'Y'
		print("Attempting to recover using unique_problem_EIDs_ARRAY")
		recoveredEIDs = iterate_through_EID_list_file_and_write_data(argumentValues,csvwriter,unique_problem_EIDs_ARRAY,reprocessTag,suppliedURL='')
		print("recoveredEIDs using unique_problem_EIDs_ARRAY: "+str(recoveredEIDs))
		
		filename = "#final_summary_EIDs.txt"
		stringToWrite = "\nRecoveredEIDs from unique_problem_EIDs_ARRAY: "+str(recoveredEIDs)
		write_to_file(filename,stringToWrite)
		
		global unique_problem_URL_ARRAY2
		unique_problem_URL_ARRAY2 = uniquify_Array(problem_URL_ARRAY2)
		len_unique_problem_URL_ARRAY2 = len(unique_problem_URL_ARRAY2)
		if len_unique_problem_URL_ARRAY2 > 0:
			print("Attempting to recover using problem_URL_ARRAY2")
			EID_List_to_Process = ''
			totalProcessedEIDs = 0
			
			for i in range(0,len_unique_problem_URL_ARRAY2):
				suppliedURL = unique_problem_URL_ARRAY2[i]
				recEIDs2 = process_EID_data(csvwriter,EID_List_to_Process,argumentValues,totalProcessedEIDs,suppliedURL,reprocessTag='Y')
				totalProcessedEIDs = totalProcessedEIDs + recEIDs2
				recoveredEIDs2 = recoveredEIDs2 + recEIDs2
				
			print("recoveredEIDs using problem_URL_ARRAY2: "+str(recoveredEIDs2))
			filename = "#final_summary_EIDs.txt"
			stringToWrite = "RecoveredEIDs from problem_URL_ARRAY2: "+str(recoveredEIDs2)+"\n"
			write_to_file(filename,stringToWrite)
		
		recoveredEIDs = recoveredEIDs + recoveredEIDs2
		print("\n\nSUCCESSFULLY RECOVERED "+str(recoveredEIDs)+" RE-PROCESSED EIDs")
		
	if len(unique_successful_EIDs_ARRAY) > 0: ## this is generally the case. Print and write the array contents IRRESPECTIVE of pEID_array but ONLY if there are successful EIDs. 
		print_and_write_ArrayDataContents(problem_EIDs_ARRAY,'problem_EIDs_ARRAY',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(unique_problem_EIDs_ARRAY,'#unique_problem_EIDs_ARRAY',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(successful_EIDs_ARRAY,'successful_EIDs_ARRAY',toPrint=0,toWrite=1) ## this is too large may not very useful.
		# #file_name = str(len(successful_EIDs_ARRAY))+"_successful_URL_ARRAY.txt"
		# #stringToWrite = "There are "+str(len(successful_EIDs_ARRAY))+" non-unique successful EIDs.\nThese are not printed here because the list and file is too large and not very useful."
		# #write_to_file(file_name,stringToWrite)
		print_and_write_ArrayDataContents(unique_successful_EIDs_ARRAY,'unique_successful_EIDs_ARRAY',toPrint=0,toWrite=1)
		
		## The following has been moved to write_final_summary_EIDs_File(processFlagCount =2)
		# global unique_problem_EIDs_ARRAY2
		# unique_problem_EIDs_ARRAY2 = uniquify_Array(problem_EIDs_ARRAY2)
		# print_and_write_ArrayDataContents(problem_EIDs_ARRAY2,'problem_EIDs_ARRAY2',toPrint=0,toWrite=1)
		# print_and_write_ArrayDataContents(unique_problem_EIDs_ARRAY2,'unique_problem_EIDs_ARRAY2',toPrint=0,toWrite=1)
		
		global unique_successful_EIDs_ARRAY2
		unique_successful_EIDs_ARRAY2 = uniquify_Array(successful_EIDs_ARRAY2)
		print_and_write_ArrayDataContents(successful_EIDs_ARRAY2,'successful_EIDs_ARRAY2',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(unique_successful_EIDs_ARRAY2,'unique_successful_EIDs_ARRAY2',toPrint=0,toWrite=1)
		
	if processFlagCount == 2: ## this is ONLY true if pEID_array had any records
		#print_and_write_ArrayDataContents(DATA_WRITTEN_TO_CSV,'DATA_WRITTEN_TO_CSV',toPrint=0,toWrite=0)
		file_name = str(len(DATA_WRITTEN_TO_CSV))+"_DATA_WRITTEN_TO_CSV.txt"
		stringToWrite = "There are "+str(len(DATA_WRITTEN_TO_CSV))+" non-unique successful DATA_WRITTEN_TO_CSV.\nThese are not printed here because the list and file is too large and not very useful."
		write_to_file(file_name,stringToWrite)
		global UNIQUE_DATA_WRITTEN_TO_CSV
		UNIQUE_DATA_WRITTEN_TO_CSV = uniquify_Array(DATA_WRITTEN_TO_CSV)
		#print_and_write_ArrayDataContents(UNIQUE_DATA_WRITTEN_TO_CSV,'UNIQUE_DATA_WRITTEN_TO_CSV',toPrint=0,toWrite=1)
		
		with open(str(len(UNIQUE_DATA_WRITTEN_TO_CSV))+'_UNIQUE_DATA_WRITTEN_TO_CSV_' + time.strftime("%d%m%Y-%H%M") + '.csv', 'w', newline='',encoding='utf-8') as csvfile2: ## Open the csv file------------------1
			csvwriter2 = csv.writer(csvfile2, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
			write_data_to_CSV(csvwriter2,HEADER) ##write HEADER ONCE
			print("\nWriting csvfile2: UNIQUE_DATA_WRITTEN_TO_CSV...")
			for i in range(0,len(UNIQUE_DATA_WRITTEN_TO_CSV)):
				processedData_array2 = UNIQUE_DATA_WRITTEN_TO_CSV[i]
				#csvwriter2.writerow(processedData_array2[0:len(processedData_array2)]) ## write data while looping-----------------------------------------------------------3b
				write_data_to_CSV(csvwriter2,processedData_array2)
			print("\nFinished writing csvfile2: UNIQUE_DATA_WRITTEN_TO_CSV")
			csvfile2.close() ## Close csv-------------------------4
			
		write_final_summary_EIDs_File(processFlagCount)
		
	write_EID_OTHERLIST_ARRAY_to_CSV() ## this is done at the end irrespective of processFlagCount value
	
	file_to_write = "check_processed_records_from_all_EID.txt"
	stringToWrite = "stats AFTER reprocess:\n Final EIDs processed = "+str(EID_COUNTER)+", Total EIDs in File = "+str(EIDS_IN_FILE)+", Difference = "+str(EIDS_IN_FILE - EID_COUNTER)
	write_to_file(file_to_write,stringToWrite)
	
	return;

def MAIN_EID():
	filename_location = select_file_and_initiate_variables() ## retreives the location of the user-selected EID list
	
	argumentValues = ['APIkey', 'encodingFormat'] ## defining an array of TWO elements that will contain the values for the API key and other related arguments
	argumentValues = getArgumentValues()
	
	print('\nEID list located in: '+str(filename_location))
	print('\nThere are '+str(EIDS_IN_FILE)+' EIDs in the file')
	
	filename = "#final_summary_EIDs.txt"
	stringToWrite = "File of EIDs located in: "+str(filename_location)+"\n"
	write_to_file(filename,stringToWrite)
	
	with open('#PublicationRecords_from_EID_List_' + time.strftime("%d%m%Y-%H%M") + '.csv', 'w', newline='',encoding=defaultEncodingFormat) as csvfile: ## Open the csv file------------------1
		csvwriter = csv.writer(csvfile, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
		print("\nINITIATING CSV data file to write...")
		
		header = generate_header(csvwriter,suppliedHeader='') ## write header ONCE
		#print (header)
		print("\nHEADER written to file.")
		print("Writing DATA (if exists)...\n")
		
		supplied_EID_List = []
		EIDcount = iterate_through_EID_list_file_and_write_data(argumentValues,csvwriter,supplied_EID_List,reprocessTag='N',suppliedURL='')
		
		if EIDcount == 0: ## no EID data in file. Exit directly.
			print("\nWarning: number of EIDs = "+str(EIDcount)+". No data has been written to file!!!")
			
			stringToWrite = "\nWarning: number of EIDs = "+str(EIDcount)+" (ZERO). No data has been written to file!!!"
			write_to_file(filename,stringToWrite)
			
		else: ## write final summary, validate and re-process problem EIDs if needed
			finalise_validaton_and_logfiles(csvwriter,argumentValues)
			
		print("\n\nThe API key has been used "+str(API_KEY_USAGE)+ " times for this exercise.\n")
		
		stringToWrite = "\n\nDetails from 'check_processed_records_from_all_EID.txt':\n"
		write_to_file(filename,stringToWrite)
		
		## the following copies the final summary from check_processed_records_from_all_EID.txt and writes to #final_summary_EIDs.txt
		with open('check_processed_records_from_all_EID.txt') as source_file:
			with open (filename, 'a') as sink_file:
				for line in source_file:
					if len(line) > 7 and '========' not in line: ## len of '2-s2.0' is 7. ALL valid EIDs MUST be greater than 7 in length
						#print("len(line): "+str(len(line)))
						sink_file.write('\t'+line)
						
		stringToWrite = "\n\nThe API key has been used "+str(API_KEY_USAGE)+ " times for this exercise.\n"
		write_to_file(filename,stringToWrite)
		
		# print("The following ARRAYS are written optionally (program may crash if unicode error encountered):")
		# #print_and_write_ArrayDataContents(EID_FUNDERS_ARRAY,'EID_FUNDERS_ARRAY',toPrint=0,toWrite=1)
		# print_and_write_ArrayDataContents(EID_AUTHORS_ARRAY,'EID_AUTHORS_ARRAY',toPrint=0,toWrite=1)
		# print_and_write_ArrayDataContents(EID_AFILLIATIONS_ARRAY,'EID_AFILLIATIONS_ARRAY',toPrint=0,toWrite=1)
		
		print("\nNow EXITTING")
		csvfile.close() ## Close csv-------------------------4
		print("	Publications data CSV file CLOSED")
		return;


MAIN_EID()
