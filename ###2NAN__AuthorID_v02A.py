##==============================================================================================================================================================
## Date: 10 Jan 2020
## Author: Naveed Nadvi
## Description: Asks user to select a list of Scopus AuthIDs and returns a CSV file with Author ORCID and CurrentAffiliation
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
##								MAIN_AuthID()
##
##
## NOTE: At the end of execution, look carefully at entries in problem_AuthIDs_ARRAY2. Run these AuthIDs through the web interface
## 		 to confirm all remaining AuthIDs in this list ARE invalid/illegal. If not, re-run the script with this list and append 
##		 the CSV outputs to the main CSV.
##
##==============================================================================================================================================================
'''
BASIC FLOWCHART:

read a list of scopusAuthIDs (auIDs).
	store the list into an array.
initiate log files and global arrays and variables
in blocks of 25 (max allowable for Scopus Search) do the following:
	generate the URL {only the AuthIDs will change, all other parameters stay the same}
	store the URL_output
	parse the URL_output as follows:
		create array of AuthIDs (max 25, CAN be less): extractXML with <entry> tags
		for every AuthID, harvest data: extractXML with individual tags

			•         AuthorID
			•         AuthPreferredName
			•         AuthORCID
			•         CurrentAffiliation
			•         NameVariants
			

			This is where it will be easier to check for missing data and if needed, assigning 'noData' value
			Authors can have multiple name variants - only use Preferred Name AND ONE current affiliation (if available)
			
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

proxy_support = urllib.request.ProxyHandler({"http":"web-cache-ext.usyd.edu.au:8080"}) ## Use USYD proxy server
opener = urllib.request.build_opener(proxy_support) ## Build Proxy server
urllib.request.install_opener(opener) ## Install Proxy server
##======================================================================================================================================


##======================================================================================================================================
## DEFINING DEFAULT GLOBAL VARIABLES AND WORKING DIRECTORIES SPECIFIC FOR THIS SCRIPT
##------------------------------------------------------------------------------------------------------------------------------
os.chdir("C:\\SET YOUR OWN WORKING DIRECTORY") ## NEED TO CHANGE WORKING DIRECTORY!!!

defaultAuthID = '23474803499' # a random number - not sure if it is valid!
defaultItemsPerPage = 25 ## This is the maximum that is ALLOWED for Author Search API!
defaultEncodingFormat = 'utf-8'
defaultAPI_Key = "6aaddca6e1094cbc56ae668717bac664" ## This is a random API key. Need to register with Scopus for your own

elsevierAuthorSearchToken = "https://api.elsevier.com/content/search/author?" ## other specific search tokens can be stored for ease
viewAuthID = '' ## Not relevant for Author Search; for EIDs it is '&view=COMPLETE'; view can be 'STANDARD' or 'COMPLETE' (both max 25 per page). Need COMPLETE to pull EID data
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
						['<entry>', '</entry>', 'AuthorEntries'],
						['<dc:identifier>', '</dc:identifier>', 'AuthorID'], ##value prefixed by "AUTHOR_ID:" this is spliced out in the script
						['<preferred-name>', '</preferred-name>', 'AuthorPreferredName'], ## it is a 'super tag'; not used from output
						['<orcid>', '</orcid>', 'AuthorORCID'],
						['<affiliation-name>', '</affiliation-name>', 'CurrentAffiliation'],
						['<name-variant>', '</name-variant>', 'AuthorNameVariantList'] ## multiple variants are possible; not used from output
					]

## This 'sub' tag array is common for both 'AuthorPreferredName' and 'AuthorNameVariantList'
## The separately generated AuthID_NAME_VARIATIONS file is used to recover Preferred name per AuthID
AUTHORNAME_SPECIFIC_TAG_PAIR_ARRAY = [
										['<surname>', '</surname>', 'AuthorSurname'],
										['<given-name>', '</given-name>', 'AuthorGivenName'],
										['<initials>', '</initials>', 'AuthorInitials']
									]

##======================================================================================================================================



##======================================================================================================================================
## THE FOLLOWING ARRAYS ARE SPECIFIC FOR THIS SCRIPT AND SHOULD NEVER BE RESET OR REPLACED!!!
##------------------------------------------------------------------------------------------------------------------------------

HEADER = [
			'AuthID',
			'AuthorPreferredName (ignore)',
			'AuthORCID',
			'CurrentAffiliation',        
			'AuthorNameVariantList (ignore)'
		]

LOG_FILE_ARRAY = [
					'AuthID_extract_xml_data_error_file','AuthID_E404_invalid_queries'
					,'AuthID_E400_error_file_maximum_request_exceeded'
					,'AuthID_E500_error_file_back-end_processing_error'
					,'AuthID_other_error_file'
					,'AuthID_another_error_file_non_http_other_errors'
					,'AuthID_data_error_file'
					,'check_processed_records_from_all_AuthID'
					,'#final_summary_AuthIDs'
					,'error_file_problem_URL_ARRAY' ## this file is only created to store the raw URLs, which by itself is not very useful
					,'error_file_problem_URL_ARRAY2' ## this file is only created to store the raw URLs, which by itself is not very useful
				]
##======================================================================================================================================



##======================================================================================================================================
## THE FOLLOWING GLOBAL VARIABLES STORE VALUES DURING PROGRAM EXECUTION AND NEEDS TO BE RESET FOR THE NEXT EXECUTION
##------------------------------------------------------------------------------------------------------------------------------
AuthID_LIST = [] ## stores AuthIDs from the input file to memory
problem_AuthIDs_ARRAY = [] ## to store AuthIDs with errors -- this is BETTER than storing problem_URLs because each URL is composed of multiple AuthIDs, some of which may be successful
successful_AuthIDs_ARRAY = [] ## to store successfully processed AuthIDs -- this is BETTER than storing problem_URLs because each URL is composed of multiple AuthIDs, some of which may be successful
problem_AuthIDs_ARRAY2 = [] ## to store if new errors come up during re-processing
successful_AuthIDs_ARRAY2 = [] ## to store successfully processed AuthIDs during re-processing

#problem_URL_ARRAY = [] ## THIS ARRAY HAS BEEN REMOVED FOR SIMPLICITY
problem_URL_ARRAY2 = []
unique_problem_URL_ARRAY2 = []

AUTHID_NAME_VARIATIONS_ARRAY = [] ## this stores name variations for each AuthorID in Scopus (e.g. {Nadvi| Naveed A.| N.A.}, {Nadvi| Naveed Ahmed| N.A.} for author Nadvi, N.A. (AuthorID 23474803400)

unique_problem_AuthIDs_ARRAY = [] ## to store unique AuthIDs with errors
unique_successful_AuthIDs_ARRAY = [] ## to store unique successful AuthIDs
unique_problem_AuthIDs_ARRAY2 = [] ## to store if new errors come up during re-processing
unique_successful_AuthIDs_ARRAY2 = [] ## to store successful unique AuthIDs during re-processing

DATA_WRITTEN_TO_CSV = [] ## to store row-data written to csv
UNIQUE_DATA_WRITTEN_TO_CSV = [] ## to store UNIQUE row-data written to csv

API_KEY_USAGE = 0 ## this counter stores the usage for the given API key
AuthID_COUNTER = 0 ## this counter stores the successful AuthIDs processed so far
AuthIDS_IN_FILE = 0 ## this variable stores the number of AuthIDs present in the supplied file.

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
## 1. Open a file containing list of AuthIDs (one line of AuthID per row)
	root = tkinter.Tk()
	root.withdraw()
	filename_location = tkinter.filedialog.askopenfilename() # user select input file
	
	reset_global_variables_and_logfiles()
	
	AuthID_File = open(filename_location,'r')  ## Open text file containing the list
	file_to_write = "#final_summary_AuthIDs.txt"
	number_of_AuthIDs = 0
	nonUnique_AuthID_LIST = []
	for line in AuthID_File:
		AuthID = line.strip() ## removes any newline characters and whitespaces
		if len(AuthID) > 7 and AuthID != '': ## len of '2-s2.0' is 7. ALL valid AuthIDs MUST be greater than 7 in length
			nonUnique_AuthID_LIST.append(AuthID)
			number_of_AuthIDs = number_of_AuthIDs + 1
			
	if number_of_AuthIDs == 0:
		print("Warning: File has no AuthIDs!!!")
		stringToWrite = "Warning: File has no AuthIDs!!!"
		write_to_file(file_to_write,stringToWrite)
		
	else: 
		global AuthID_LIST
		AuthID_LIST = uniquify_Array(nonUnique_AuthID_LIST)
		
		global AuthIDS_IN_FILE
		AuthIDS_IN_FILE = len(AuthID_LIST)
		
		print('\n'+str(AuthIDS_IN_FILE)+" UNIQUE AuthID(s) to process ("+str(number_of_AuthIDs)+" were supplied in file).")
		stringToWrite = str(AuthIDS_IN_FILE)+" UNIQUE AuthID(s) to process ("+str(number_of_AuthIDs)+" were supplied in file)."
		write_to_file(file_to_write,stringToWrite)
		
	return filename_location;

## this function, run at the start of execution is needed if the same script is re-run at the prompt.
## If not reset, the values of the global variables from the previous run remain stored in memory.
def reset_global_variables_and_logfiles():
	print("Initiating all log files - not all (error) files may have records:")
	now = datetime.datetime.now()
	
	for logfile in LOG_FILE_ARRAY:
		filename = logfile+'.txt'
		print("\t"+filename)
		stringToWrite = "\n========NEW RECORDS: "+now.strftime("%Y%m%d_%H:%M:%S")+"========-----------------\n\n"
		write_to_file(filename,stringToWrite)
	
	print("\nResetting the global ARRAYs and COUNTER VARIABLEs.")
	
	AuthID_LIST[:] = [] ## resetting to store new AuthIDs from new input file to memory
	problem_AuthIDs_ARRAY[:] = [] ## resetting to store AuthIDs with errors for the following execution
	successful_AuthIDs_ARRAY[:] = [] ## resetting to store successful AuthIDs for the following execution
	problem_AuthIDs_ARRAY2[:] = [] ## resetting to store if new errors come up during re-processing for the following execution
	successful_AuthIDs_ARRAY2[:] = [] ## resetting to store successful AuthIDs during re-processing for the following execution
	
	problem_URL_ARRAY2[:] = []
	unique_problem_URL_ARRAY2[:] = []
	
	AUTHID_NAME_VARIATIONS_ARRAY[:] = []
	
	unique_problem_AuthIDs_ARRAY[:] = [] ## resetting to store unique AuthIDs with errors for the following execution
	unique_successful_AuthIDs_ARRAY[:] = [] ## resetting to store unique successful AuthIDs for the following execution
	unique_problem_AuthIDs_ARRAY2[:] = [] ## resetting to store if new errors come up during re-processing for the following execution
	unique_successful_AuthIDs_ARRAY2[:] = [] ## resetting to store successful unique AuthIDs during re-processing for the following execution
	
	DATA_WRITTEN_TO_CSV[:] = [] ## resetting to store row-data written to csv for the following execution
	UNIQUE_DATA_WRITTEN_TO_CSV[:] = [] ## resetting to store UNIQUE row-data written to csv for the following execution
	
	global API_KEY_USAGE ## specifying the GLOBAL VARIABLE
	API_KEY_USAGE = 0
	global AuthID_COUNTER
	AuthID_COUNTER = 0
	global AuthIDS_IN_FILE
	AuthIDS_IN_FILE = 0
	
	len_and_values_after_reset = int(AuthIDS_IN_FILE+AuthID_COUNTER+API_KEY_USAGE
									+len(DATA_WRITTEN_TO_CSV)+len(UNIQUE_DATA_WRITTEN_TO_CSV)
									+len(successful_AuthIDs_ARRAY)+len(problem_AuthIDs_ARRAY2)+len(successful_AuthIDs_ARRAY2)
									+len(unique_problem_AuthIDs_ARRAY)+len(unique_successful_AuthIDs_ARRAY)+len(unique_problem_AuthIDs_ARRAY2)
									+len(unique_successful_AuthIDs_ARRAY2)+len(AuthID_LIST)+len(problem_AuthIDs_ARRAY)+len(problem_URL_ARRAY2)
									+len(unique_problem_URL_ARRAY2)+len(AUTHID_NAME_VARIATIONS_ARRAY))
									
	print("\nConfirming reset: Total length of ARRAYs & VARIABLE values = "+str(len_and_values_after_reset)+" (should be ZERO)\n")
	filename = "#final_summary_AuthIDs.txt"
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
		
	##apiKey = input("Please provide API Key or hit ENTER to use default key: ")
	apiKey = defaultAPI_Key 
	
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

#typical URL=
#https://api.elsevier.com/content/search/author?query=%28au-id%2823474803400%29%20or%20au-id%287006682720%29%29&httpAccept=application/xml&apiKey=7f592e39046a1428efc18dbf075455fc

## t = generate_AuthID_URL()
def generate_AuthID_URL(AuthID_List_to_Process, reprocessTag = 'N', apiKey = defaultAPI_Key):
	# elsevierAuthorSearchToken = "https://api.elsevier.com/content/search/author?" ## other specific search tokens can be stored for ease
	# viewAuthID = '' ##no view options for AuthID API!
	# responseGenerator = '&httpAccept=application/xml'
	
	URL = "valid url not defined yet"
	
	AuthIDs = len(AuthID_List_to_Process)	
	if AuthIDs > 0: #and AuthIDs <= 25:
		AuthID_String = ''
		for i in range(0,AuthIDs):
			AuthID = AuthID_List_to_Process[i]
			if i < AuthIDs-1: ## there are more records
				string = '+au-id%28'+str(AuthID)+'%29+OR' ## append an 'OR' clause if the AuthID is NOT the last entry
			else: ## this is the last record
				string = '+au-id%28'+str(AuthID)+'%29+' ## do NOT append an 'OR' clause if the AuthID is the last entry
			AuthID_String = AuthID_String + string
			
		queryAuthID = 'query=%28'+str(AuthID_String)+'%29'
		URL = elsevierAuthorSearchToken + queryAuthID + viewAuthID + responseGenerator + "&apiKey="+apiKey
	
	else: ## any other illegal values --SHOULD NEVER HAPPEN
		print("\nWarning: len(AuthID_List_to_Process) is NOT > 0.")
		print(" List CAN be empty if ALL remaining AuthIDs are ILLEGALs before \nnumber_of_iterations has been completed.")
		if reprocessTag == 'N':
			print("  These missed AuthIDs will be reprocessed.\n")
	#print ('generatedURL:\n',URL)
	return URL;

## t = output_from_URL('https://api.elsevier.com/content/search/author?query=%28au-id%2823474803400%29%20or%20au-id%287006682720%29%29&httpAccept=application/xml&apiKey=7f592e39046a1428efc18dbf075455fc')
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
			write_to_file(file_problem_URL_ARRAY2, URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			problem_URL_ARRAY2.append(URL) ## stores the URL with mismatched tags.
		else:
			write_to_file(file_problem_URL_ARRAY, URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags - THIS ARRAY HAS BEEN REMOVED FOR SIMPLICITY
			
		if err.code == 404:
			print(' - '+now.strftime("%H:%M:%S")+" - ERROR 404: INVALID AuthID or query")
			filename = "AuthID_E404_invalid_queries.txt"
			stringToWrite = ' - '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
		elif err.code == 400:
			print(' - '+now.strftime("%H:%M:%S")+" - ERROR: EXCEEDED MAX NUMBER ALLOWED FOR THE SERVICE LEVEL")
			filename = "AuthID_E400_error_file_maximum_request_exceeded.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
		elif err.code == 500:
			print(' - '+now.strftime("%H:%M:%S")+" - SYSTEM_ERROR: A failure has occurred within Scopus")
			filename = "AuthID_E500_error_file_back-end_processing_error.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(10) ## give more time here for Scopus system to recover
			
		else:
			print(' - '+now.strftime("%H:%M:%S")+" - HTTP ERROR: UNSURE OF CAUSE")
			filename = "AuthID_other_error_file.txt"
			stringToWrite = ' - ERROR '+str(err.code)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
			write_to_file(filename,stringToWrite)
			time.sleep(5)
			
	except: ## non-HTTP exception
		now = datetime.datetime.now()
		print(' - '+now.strftime("%H:%M:%S")+" - ERROR: NON HTTP UNSURE OF CAUSE")
		error_txt = 'ERROR_non_http'
		
		if reprocessTag == 'Y':
			write_to_file(file_problem_URL_ARRAY2, URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			problem_URL_ARRAY2.append(URL) ## stores the URL with mismatched tags.
			
		else:
			write_to_file(file_problem_URL_ARRAY, URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags -  THIS ARRAY HAS BEEN REMOVED FOR SIMPLICITY.
			
		filename = "AuthID_another_error_file_non_http_other_errors.txt"
		stringToWrite = ' - '+str(error_txt)+' - '+now.strftime("%H:%M:%S")+' - '+URL+'\n'
		write_to_file(filename,stringToWrite)
		time.sleep(5)
		
	totalResultsStartTag = START_END_TAGS_ARRAY[0][0]
	totalResultsEndTag = START_END_TAGS_ARRAY[0][1]
	queryID = START_END_TAGS_ARRAY[0][2]
	#print("here1")
	totalResults_array = extract_xml_data(queryID,URL,URL_output,totalResultsStartTag,totalResultsEndTag,description='') ## a 1-element array for the size of result set (can be 0-the maximum allowable - CHECK!)
	print("len(totalResults_array) is "+str(len(totalResults_array)))
	
	if len(totalResults_array) >= 1: ## there is at least ONE valid AuthID with data (in fact, this value should ONLY BE ONE)
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
	filename = "AuthID_data_error_file.txt"
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
## queryID can be processed ScopusID, AuthID, afID etc., depending on the actual script being run. description describes the queryID's specific tagged-data fields
####========================================================================================================================================================================================
def extract_xml_data(queryID, URL, URL_output, starttag, endtag, description = ''):
	output = [] ## creating an empty array. when valid, it will contain the relevant extracted URL_output. In case of number-mismatch error the invalid output will be ignored by the invoking code
	repition = 0 ## this counter keeps track of repeat runs for the mismatch error check before storing it for re-process
	filename = "AuthID_extract_xml_data_error_file.txt"
	
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
					problem_AuthIDs_ARRAY.append(queryID) ## ONLY append queryID (which will be a AuthID) if a non-null description is passed to the function
					description = ' (mismatch for: '+description+')'
					
				stringToWrite = now.strftime("%H:%M:%S")+' - '+'FAILED 5 TIMES FOR queryID: '+queryID+description+'\n'
				write_to_file(filename,stringToWrite)
				
				write_to_file('error_file_problem_URL_ARRAY', URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
				#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags -  THIS ARRAY HAS BEEN REMOVED FOR SIMPLICITY.
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
## AFID_List--  one row per AF-ID, AfName, City, Country, Aff_url
## AuthorsList-- one row per AuthName, AU-ID, AuORCID, AF-ID, Au_url
## FundingDetails-- one row per fund-sponsor, fund-acr, fund-no
## AuthorNameVariantList-- one row per author name variation including Surname, Given name, Initials
##==========================================================================================
def process_multiple_data_value_list(cell_data_array,queryID,description):
	now = datetime.datetime.now()
	detailed_tag_pair_array = [] ## stores the tag details that are specific to the description passed as argument
	AuthIDvalue = [queryID] ## stores the AuthID as the first element of the final (valid) multiple_data_array that will be returned
	multiple_data_array = [] ## this array will store the processed data
	temp_array_of_array = [] ## temporarily store multiple_data_array to obtain transposed element (names/IDs) only
	need_to_process_multiple_data = 'yes' ## detailed_tag_pair_array will be traversed if this is 'yes' (default value)
	#pass  
	
	if description == 'AuthorNameVariantList' or description == 'AuthorPreferredName':
		#print("Special description: "+description)
		detailed_tag_pair_array = AUTHORNAME_SPECIFIC_TAG_PAIR_ARRAY
		
		#pass
		
	else:
		print("ERROR: "+description+" has multiple values")
		filename = "AuthID_data_error_file.txt"
		stringToWrite = now.strftime("%H:%M:%S")+' - * - '+description+" for AuthID "+str(queryID)+" has multiple values.\n"
		write_to_file(filename,stringToWrite)
		multiple_data_array = cell_data_array ## returns the supplied cell_data_array as no detailed_tag_pair_array are relevant 
		
		need_to_process_multiple_data = 'no' ## detailed_tag_pair_array will NOT be traversed
		
	if need_to_process_multiple_data == 'yes':
		startIndex = 0
		endIndex = len(detailed_tag_pair_array)
		for cell_data in cell_data_array:
			URL = 'within process_multiple_data_value_list(); AuthID='+queryID+',recursion_enabled=no'
			remaining_row_data_array = harvest_remaining_cell_data(startIndex,endIndex,queryID,URL,cell_data,detailed_tag_pair_array,recursion_enabled='no') ## returns the remaining data
			
			if remaining_row_data_array[0] == -1:
				print("harvest_remaining_cell_data() returned illegal/error value for AuthID: "+queryID)
				multiple_data_array = [-1]
				multiple_data_array.append(queryID)
				
			else: ## everything worked normally
				multiple_data_array = AuthIDvalue + remaining_row_data_array ## combines the first data (AuthID) with its respective remaining data
				temp_array_of_array.append(multiple_data_array)
				
				## the following appends multiple_data_array to the respective global AuthID_***_ARRAYS for final printing in the end
				if description == 'AuthorNameVariantList':
					multiple_data_array = multiple_data_array + ['Variant']
					AUTHID_NAME_VARIATIONS_ARRAY.append(multiple_data_array)

				elif description == 'AuthorPreferredName':
					multiple_data_array = multiple_data_array + ['Preferred']
					AUTHID_NAME_VARIATIONS_ARRAY.append(multiple_data_array)
					
				else:
					print("The supplied cell_data_array is returned as is \n  since no detailed_tag_pair_array are relevant for "+description)
					
			
		temp_array_of_array = uniquify_Array(temp_array_of_array) ## remove duplicated records
		if len(temp_array_of_array) > 1: ## when there are more than one UNIQUE multiple_data_array appended
			temp_array_of_array = transposeArrayOfArray(temp_array_of_array) ## transposing the array
			multiple_data_array = temp_array_of_array[1] ## the first element is AuthID, the second element is names/IDs
			
		elif len(temp_array_of_array) <= 0: ## this must NEVER HAPPEN
			print("ERROR: len(temp_array_of_array)<=0 for AuthID: "+queryID)
			multiple_data_array = [-1]
			multiple_data_array.append(queryID)
			
		else: ## len(temp_array_of_array)==1; the single instance of the SAME multiple_data_array is returned
			#print("len(temp_array_of_array)= "+str(len(temp_array_of_array)))
			single_value = str(temp_array_of_array[0][1]) ## second element of the first (and ONLY) array of temp_array_of_array is the name/ID 
			multiple_data_array = [single_value]
			
	return multiple_data_array;

##==============================================================================
## at its current simplified state, this function just returns the cell_data back
## as a string. but other versions had specifically addressed (e)ISSN formats. in 
## short, this function can be used to modify cell data format depending on the 
## need if necessary.
##==============================================================================
def format_cell_data(description, cell_data, queryID):
	# now = datetime.datetime.now()
	# if description == 'PubISSN' or description == 'Pub_eISSN':
		# if len(cell_data) != 8: ## a valid (raw) e/ISSN must ALWAYS be 8 characters (before the hyphen is inserted). typical formatted e/ISSN is 1234-5678
			# print("Invalid "+description+" for AuthID "+str(queryID)+": "+str(cell_data))
			# filename = "AuthID_data_error_file.txt"
			# stringToWrite = now.strftime("%H:%M:%S")+' - * - '+"Invalid "+description+" for AuthID "+str(queryID)+": "+str(cell_data)+".\n"
			# write_to_file(filename,stringToWrite)
			
			# filename2 = "#AuthIDs_with_invalid_(e)ISSN"
			# stringToWrite = str(queryID)+": "+str(cell_data)
			# write_to_file(filename2,stringToWrite)
			
		# left_substr = cell_data[:4]
		# right_substr = cell_data[4:]
		# cell_data = str(left_substr+'-'+right_substr)
		
	# else:
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
		
		cell_data_array = extract_xml_data(queryID,URL,data,starttag,endtag,description) ## extracting data for non-AuthID 'DESCRIPTION' field (size can be 0 or more)
		if cell_data_array == ['Number mismatch']: ## XML mismatch occured so assign error state
			print("ERROR: cell_data_array == ['Number mismatch'] for queryID: "+queryID)
			remaining_row_data_array = [-1] ## returns an illegal value to indicate error and ignores all subsequent calculations
			remaining_row_data_array.append(queryID)
			
		else: ## no XML mismatch occured for non-AuthID data so proceed with further extraction; NOTE, MIN size of cell_data_arra is 0 and there are no MAX limit
			size_of_cell_data_array = validatedArraySize(cell_data_array,queryID,min_error_value=-1,max_error_value='',function_name='harvest_remaining_cell_data')
			if size_of_cell_data_array == 0: 
				cell_data = str('no '+description+' data available')
				filename = "#AuthIDs_with_no_"+description
				stringToWrite = str(queryID)
				write_to_file(filename,stringToWrite)
				
			elif size_of_cell_data_array > 1 or description == 'AuthorPreferredName':
				if recursion_enabled == 'yes':
					multiple_data_array = process_multiple_data_value_list(cell_data_array,queryID,description) ##<--------------$$$$$$$$$$ DEVELOP THIS FURTHER
					if multiple_data_array[0] == -1:
						print("process_multiple_data_value_list() returned illegal/error value for AuthID: "+queryID)
						remaining_row_data_array = [-1] ## returns an illegal value to indicate error and ignores all subsequent calculations
						remaining_row_data_array.append(queryID)
						
					else:
						cell_data = convert_multiple_data_array_to_stringList(multiple_data_array,description,queryID)
						
				else: ## when recursion is DISABLED: this is typically when called from process_multiple_data_value_list()
					cell_data = convert_multiple_data_array_to_stringList(cell_data_array,description,queryID)

			elif size_of_cell_data_array == 1: 
				cell_data = str(cell_data_array[0])
				cell_data = format_cell_data(description,cell_data,queryID) ## this should potentially be at the end of the else clause before remaining_row_data.append(cell_data)
				
			else: ## size_of_cell_data_array can't be -ve EVER!!!
				print("ERROR!!! size_of_cell_data_array is less than zero: "+str(size_of_cell_data_array)) 
				cell_data = str('ERROR: -veArraySize for_'+description)
				
			#cell_data = format_cell_data(description,cell_data,queryID) ## this should potentially be at the end of the else clause before remaining_row_data.append(cell_data)
			remaining_row_data_array.append(cell_data) ## this is here to ensure data is appended ONLY if no XML mismatch occured for non-AuthID field(s)
						
	return remaining_row_data_array;

def create_AuthID_data_Array_of_array(URL, URL_output, totalProcessedAuthIDs):	
	#now = datetime.datetime.now()
	
	ErrorStatus = 'No Errors So Far...' ## this is a flag for which the value of -1 indicates an error state; after successful execution it indicates number of AuthIDs processed successfuly. 
	#AuthID_row_data_array = [] ## defining an array to contain each row of data for a given AuthID
	AuthID_data_Array_of_array = [] ## creating an empty array of array that will hold all the successfully processed AuthID_row_data_array
	
	entryStartTag = START_END_TAGS_ARRAY[1][0]
	entryEndTag = START_END_TAGS_ARRAY[1][1]
	entryDescription = START_END_TAGS_ARRAY[1][2]
	startAuthIDrange = totalProcessedAuthIDs+1 ## +1 reflects the more 'intuitive' count
	endAuthIDrange = totalProcessedAuthIDs+defaultItemsPerPage ## +defaultItemsPerPage reflects the more 'intuitive' count
	queryID = entryDescription+str(startAuthIDrange)+'-'+str(endAuthIDrange) ## e.g. the first batch will be PubEntries1-25
	
	print("\nProcessing Entry_object_array: "+queryID)
	Entry_object_array = extract_xml_data(queryID,URL,URL_output,entryStartTag,entryEndTag,description='') ## an array of AuthID entries (size can be 0 to 25)
	if Entry_object_array == ['Number mismatch']: ## XML mismatch occured so assign error state
		print("ERROR: Entry_object_array == ['Number mismatch'] for queryID: "+queryID)
		ErrorStatus = -1 ## returns an illegal value to indicate error and ignores all subsequent calculations
		AuthID_data_Array_of_array = [-1]
		AuthID_data_Array_of_array.append(queryID)
		
	else: ## no XML mismatch occured for Entry_object_array so proceed with further extraction
		size_of_Entry_object_array = validatedArraySize(Entry_object_array,queryID,min_error_value=0,max_error_value=26,function_name='create_AuthID_data_Array_of_array')
		if size_of_Entry_object_array <= 0: ## or size_of_Entry_object_array >= 26: ## this should NEVER happen########<===========================&&&&&&&&&&&&&&&&&&&&&&&&&&&& CHECK THIS LOGIC: what is ths max allowable
			print("ERROR: size_of_Entry_object_array <= 0 or size_of_Entry_object_array >= 26 for queryID: "+queryID)
			ErrorStatus = -1
			AuthID_data_Array_of_array = [-1]
			AuthID_data_Array_of_array.append(queryID)
			
		else: ## do the following ONLY if there are up to 1-25 records (inclusive). The max limit CAN be less than 25 for the 'remainder' entries
			print("  AuthID entries extracted: "+str(size_of_Entry_object_array)+" of (maximum) "+str(defaultItemsPerPage)+" supllied AuthIDs")
			AuthIDstartTag = START_END_TAGS_ARRAY[2][0] ## specifically extracting from START_END_TAGS_ARRAY[2] (= AuthID tags)
			AuthIDendTag = START_END_TAGS_ARRAY[2][1] ## specifically extracting from START_END_TAGS_ARRAY[2] (= AuthID tags)
			#AuthIDdescription = START_END_TAGS_ARRAY[1][2] ## specifically extracting from START_END_TAGS_ARRAY[2] (= AuthID tags)
			
			for i in range(0,size_of_Entry_object_array):
				cell_data_array = [] ## defining a temporary array to contain each data field for a given AuthID
				Entry_object = Entry_object_array[i] ## a single-element array containing tagged-data to be placed in multiple columns is copied; Entry_object is just a (long) text entry
				queryID = 'Extracting_AuthID'+str(i+startAuthIDrange) ## +startAuthIDrange reflects the more 'intuitive' count e.g. 'Extracting_AuthID1' for the first entry (i=0)
				
				cell_data_array = extract_xml_data(queryID,URL,Entry_object,AuthIDstartTag,AuthIDendTag,description='') ## extracting the AuthID; SIZE MUST ONLY BE ONE element
				if cell_data_array == ['Number mismatch']: ## XML mismatch occured so assign error state
					print("ERROR: cell_data_array == ['Number mismatch'] for queryID: "+queryID)
					ErrorStatus = -1 ## returns an illegal value to indicate error and ignores all subsequent calculations
					AuthID_data_Array_of_array = [-1]
					AuthID_data_Array_of_array.append(queryID)
					
				else: ## no XML mismatch occured for AuthID so proceed with further extraction
					size_of_cell_data_array = validatedArraySize(cell_data_array,queryID,min_error_value=0,max_error_value=2,function_name='create_AuthID_data_Array_of_array')
					if size_of_cell_data_array != 1: ## SIZE MUST ONLY BE ONE: one AuthID per entry
						print("size_of_cell_data_array for "+queryID+" is not 1: "+str(size_of_cell_data_array))
						ErrorStatus = -1
						AuthID_data_Array_of_array = [-1]
						AuthID_data_Array_of_array.append(queryID)
						
					else: ## do this because there is one AuthID per entry
						AuthID_row_data_array = [] ## defining an array to contain each row of data for a given AuthID
						queryID  = cell_data_array[0] ## this is the AuthID, and must be the the ONLY entry in the single-element array
						queryID = queryID[10:]## the AuthorID is prefixed with "AUTHOR_ID:" (len = 10)
						AuthIDvalue = [queryID] ## AuthID is the first value to be added to AuthID_row_data_array
						#print("\nProcessing AuthID: "+queryID)
						
						startIndex = 3  ## starting at 3 because index 0 is for totalResults, 1 for Entry_object, and 2 is for AuthID - all already used above
						endIndex = len(START_END_TAGS_ARRAY)
						
						remaining_row_data_array = harvest_remaining_cell_data(startIndex,endIndex,queryID,URL,Entry_object,suppliedTagPairArray='',recursion_enabled='yes') ## returns the remaining data
						if remaining_row_data_array[0] == -1:
							print("harvest_remaining_cell_data() returned illegal/error value for AuthID: "+queryID)
							ErrorStatus = -1
							AuthID_data_Array_of_array = [-1]
							AuthID_data_Array_of_array.append(queryID)
							
						else:
							#AuthIDvalue[0] = AuthIDvalue[0][10:]
							AuthID_row_data_array = AuthIDvalue + remaining_row_data_array ## combines the first data (AuthID) with its respective remaining data
							
							len_AuthID_row_data_array = validatedArraySize(AuthID_row_data_array,queryID,min_error_value=(len(HEADER)-1),max_error_value=(len(HEADER)+1),function_name='create_AuthID_data_Array_of_array')
							if len_AuthID_row_data_array != len(HEADER): ## check that the number of data_fields match the number of columns
								print("len_AuthID_row_data_array ("+str(len_AuthID_row_data_array)+") != len(HEADER) ("+str(len(HEADER))+") for AuthID: "+queryID)
								ErrorStatus = -1
								AuthID_data_Array_of_array = [-1]
								AuthID_data_Array_of_array.append(queryID)
								
							else:
								#print("len_AuthID_row_data_array ("+str(len_AuthID_row_data_array)+") is same as len(HEADER) ("+str(len(HEADER))+").\nSuccessfully harvested all records for AuthID: "+queryID)
								AuthID_data_Array_of_array.append(AuthID_row_data_array) ## this is here to ensure AuthID_row_data_array is appended ONLY if there is a FULL row_data harvest)
							
	print("\n\nErrorStatus at the end of parsing Entry_object_array is: "+str(ErrorStatus))
			
	if len(AuthID_data_Array_of_array) == 0: ## for some reason if no data were added to AuthID_data_Array_of_array
		ErrorStatus = -1
		AuthID_data_Array_of_array = [-1]
		queryID = 'unknown queryID(no data were added to AuthID_data_Array_of_array)'
		AuthID_data_Array_of_array.append(queryID)
		
	if ErrorStatus == -1: ## Errors have been encountered due to exceptions raised during extract_xml_data()
		#AuthID_data_Array_of_array = ErrorStatus ## a negative value of -1 (from ScopusIDs) flags problem/error
		print("XML mismatches or other errors encountered in create_AuthID_data_Array_of_array(). \n\tSkipping this entry and moving to next item (if exists)...")
		
	else: ## EVERYTHING WORKED NORMALLY...
		ErrorStatus = len(AuthID_data_Array_of_array) ## should be a non-negative number if all worked normally
		print("\nSuccessfully processed "+str(ErrorStatus)+" of "+str(size_of_Entry_object_array)+" LEGAL AuthID entries.\n")
		
	return AuthID_data_Array_of_array; ## this is either an array of arrays, or a single integer value of -1 indicating error state.

##========================================================================================================
## This function loops through and writes scopusIDs and other data in blocks of 25. Also returns the 
## number of processed AuthIDcount and prints APIkey usage
##========================================================================================================
def process_AuthID_data(csvwriter, AuthID_List_to_Process, argumentValues, totalProcessedAuthIDs, suppliedURL = '', reprocessTag = 'N'): ## reprocessTag = 'N' (no; default) or 'Y' (yes)
	#now = datetime.datetime.now()
	apiKey  = argumentValues[0]
	encodingFormat = argumentValues[1]
	AuthID_data_Array_of_array = [] ## AuthID_data_Array_of_array should be EITHER a correctly structured array of row_data_array with all data ready to be written to csv file OR -1 indicating an error state
	newAuthIDcount = 0 ## this counts only the new AuthIDs being harvested (compare that to totalProcessedAuthIDs which counts the ENTIRE AuthIDs being harvested so far)
	
	if suppliedURL == '': ## no URL provided: generate NEW URL
		URL = generate_AuthID_URL(AuthID_List_to_Process,reprocessTag,apiKey)
	else:
		URL = suppliedURL ## AuthID_List_to_Process is EMPTY (and also unnecessary) when suppliedURL is NOT empty
		
	URL_output = output_from_URL(URL,encodingFormat,reprocessTag)
	if URL_output == 'Invalid output unless replaced after Exceptions handling': ## somehow an illegal URL_output has been passed
		AuthID_data_Array_of_array = [-1] ## this is the default error state unless replaced after successful extract_xml_data()
		reason = 'Invalid URL output'
		AuthID_data_Array_of_array.append(reason)
		
	else:
		AuthID_data_Array_of_array = create_AuthID_data_Array_of_array(URL,URL_output,totalProcessedAuthIDs)
			
	if AuthID_data_Array_of_array[0] == -1: ## invalid/error state from validation, most likely due to mismatch in XML tags
		reason_queryID = AuthID_data_Array_of_array[1] ## if AuthID_data_Array_of_array[0] == -1, a reason or queryID is ALWAYS appended (and array length is ALWAYS 2)
		print("Illegal state of data (AuthID_data_Array_of_array[0] == -1).\n Reason/queryID: "+reason_queryID+". len(AuthID_data_Array_of_array)= "+str(len(AuthID_data_Array_of_array))+".\n\tSkipping this and moving to next item (if exists)...")
		now = datetime.datetime.now()
		filename = "AuthID_data_error_file.txt"
		stringToWrite = now.strftime("%H:%M:%S")+' - '+reprocessTag+' - '+"Illegal state of data (AuthID_data_Array_of_array[0] == -1). Reason/queryID: "+reason_queryID+". len(AuthID_data_Array_of_array)= "+str(len(AuthID_data_Array_of_array))+".\n"
		write_to_file(filename,stringToWrite)
		
		if reprocessTag == 'Y':
			write_to_file('error_file_problem_URL_ARRAY2', URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			problem_URL_ARRAY2.append(URL)
			
		else: ## not reprocessing
			write_to_file('error_file_problem_URL_ARRAY', URL) ## writes the URL with mismatched tags (may have been caused from one or more AuthIDs)
			#problem_URL_ARRAY.append(URL) ## stores the URL with mismatched tags -  THIS ARRAY HAS BEEN REMOVED FOR SIMPLICITY
			
	else: ## a valid AuthID_data_Array_of_array has been obtained, write to CSV
		print("	Writing data to file...\n")
		
		## an inner loop here to write the records to the CSV. DO THIS ONLY IF NO EXCEPTIONS ARE RAISED AND ALL DATA IS AVAILABLE TO BE WRITTEN IN BLOCKS OF 200
		for i in range(0,len(AuthID_data_Array_of_array)):
			processedData_array = AuthID_data_Array_of_array[i]
			AuthID = processedData_array[0] ## the AuthID is *always* the first element of the array
			write_data_to_CSV(csvwriter,processedData_array)
			DATA_WRITTEN_TO_CSV.append(processedData_array)
			newAuthIDcount = newAuthIDcount + 1
			#totalProcessedAuthIDs = totalProcessedAuthIDs + 1 ## this line is unnecessary if the following print() is commented out; totalProcessedAuthIDs value expires when this function call ceases and the updated totalProcessedAuthIDs in the context of this script is updated via the newAuthIDcount that is returned to the iterate_through_AuthID_list_file_and_write_data() fuction.
			#print("\twriting AuthID record: "+str(totalProcessedAuthIDs))
					
			if reprocessTag == 'Y':
				successful_AuthIDs_ARRAY2.append(AuthID)
				write_to_file('successful_URL_ARRAY2', URL) ## writes the successfully processed URL
				#successful_URL_ARRAY2.append(URL)
				
			else: ##reprocessTag == 'N', ie, the first pass
				successful_AuthIDs_ARRAY.append(AuthID)
				write_to_file('successful_URL_ARRAY', URL) ## writes the successfully processed URL
				#successful_URL_ARRAY.append(URL)	
				
			global AuthID_COUNTER
			AuthID_COUNTER = AuthID_COUNTER + 1
			
	print("\nAuthID count= "+str(AuthID_COUNTER)+" of "+str(AuthIDS_IN_FILE)+" AuthIDs in File. APIkey used "+str(API_KEY_USAGE)+" times.")
	
	return newAuthIDcount;

def iterate_through_AuthID_list_file_and_write_data(argumentValues, csvwriter, supplied_AuthID_List, reprocessTag = 'N', suppliedURL = ''): ## reprocessTag = 'N' (no; default) or 'Y' (yes)
	maxAuthIDs_toProcess = defaultItemsPerPage	
	reprocess_description = 'Reprocessing problem_AuthIDs_ARRAY:\n'
	## an outer loop here to go through a list of AuthIDs for which to search for and retrieve relevant data
	#print("	Entering loop...")
	
	if reprocessTag == 'N': ## if NOT re-processing problem AuthIDs, then supplied_AuthID_List is the original AuthID_LIST, else supplied_AuthID_List is the unique_problem_AuthIDs_ARRAY
		supplied_AuthID_List = AuthID_LIST ## else supplied_AuthID_List is the problem_AuthIDs_ARRAY
		reprocess_description = ''
		
	len_supplied_AuthID_List = validatedArraySize(supplied_AuthID_List,queryID='supplied_AuthID_List',min_error_value=0
												,max_error_value='',function_name='iterate_through_AuthID_list_file_and_write_data') ## note, max value CAN be more than 25 if reprocessTag = 'N'
	
	number_of_iterations = int(len_supplied_AuthID_List/maxAuthIDs_toProcess)+1 ## one ADDITIONAL cycle to take care of the 'remainder'
	print(reprocess_description+"URLs need to be created "+str(number_of_iterations)+" time(s) when maxAuthIDs_toProcess = "+str(maxAuthIDs_toProcess))
	
	startSpliceIndex = 0
	endSpliceIndex = maxAuthIDs_toProcess ########<===========================&&&&&&&&&&&&&&&&&&&&&&&&&&&& CHECK THIS LOGIC: 25 or 24???
	totalProcessedAuthIDs = 0
	for itr in range(0,number_of_iterations):
		AuthID_List_to_Process = supplied_AuthID_List[startSpliceIndex:endSpliceIndex]
		newAuthIDs = process_AuthID_data(csvwriter,AuthID_List_to_Process,argumentValues,totalProcessedAuthIDs,suppliedURL,reprocessTag)
		
		startSpliceIndex = startSpliceIndex + maxAuthIDs_toProcess
		endSpliceIndex = endSpliceIndex + maxAuthIDs_toProcess
		totalProcessedAuthIDs = totalProcessedAuthIDs + newAuthIDs
		if totalProcessedAuthIDs >= len_supplied_AuthID_List:
			#print("\nSUCCESSFULLY HARVESTED ALL "+str(totalProcessedAuthIDs)+" ENTRIES OF TOTAL "+str(len_supplied_AuthID_List)+" AuthIDs.") ## this is commented because at the end of the iteration, totalProcessedAuthIDs MAY STILL BE LESS than len_supplied_AuthID_List if AuthID_LIST had illegal entries
			break
			
		else:
			print("Have more records to harvest. Increasing count by "+str(maxAuthIDs_toProcess)+" and restarting")
			
	if reprocessTag == 'N':
		print("\nDATA HARVEST COMPLETED FOR "+str(totalProcessedAuthIDs)+" *LEGAL* ENTRIES OF TOTAL "+str(len_supplied_AuthID_List)+" AuthIDs.") ## at the end of the iteration, all records are harvested
	#AuthIDcount = AuthID_COUNTER ## this is most probably redundant: AuthID_COUNTER can do the same job
	return totalProcessedAuthIDs;

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

####======================================================================================================
## Note that this function is comprised of if statements that really work as CASE clauses. There are repetitions in code, but that is 
## unavoidable because depending on what processFlagCount is passed, the code run is exclusive
####======================================================================================================
def write_final_summary_AuthIDs_File(processFlagCount): ## <---------$$$$$$$$$$$ Need to create/modify code here
	filename = "#final_summary_AuthIDs.txt"
	
	print("\nData write"+str(processFlagCount)+" complete.\n  Processed "+str(AuthID_COUNTER)+" AuthIDs (file had "+str(AuthIDS_IN_FILE)+" entries). ")
	
	stringToWrite = "\nData write"+str(processFlagCount)+" complete.\n\tProcessed "+str(AuthID_COUNTER)+" AuthIDs (file had "+str(AuthIDS_IN_FILE)+" entries)"
	write_to_file(filename,stringToWrite)
	global problem_AuthIDs_ARRAY ## specifying the GLOBAL VARIABLE (needed for adding missedAuthIDs[] below)
	missedAuthIDs = [] ## an array to store AuthIDs that were missed during data harvest; this is most likely due to illegal AuthID without any Scopus data
	for AuthID in AuthID_LIST:
		if ((AuthID != 'Trying to re-process problem AuthIDs (if any)') ## ignore "Trying to re-process problem AuthIDs" text
			and (AuthID not in problem_AuthIDs_ARRAY) and (AuthID not in successful_AuthIDs_ARRAY)): ## if AuthID is missing in BOTH successful_AuthIDs_ARRAY and problem_AuthIDs_ARRAY
			#print("\tAuthID missing in BOTH successful_ and problem_AuthIDs_ARRAY:\n "+str(AuthID)) ## mute this: too much text!!!
			missedAuthIDs.append(AuthID)
			
	if processFlagCount == 1: ## general, first-pass data write
		if AuthID_COUNTER > 0: ## the following will ONLY happen if there is AT LEAST ONE AuthID successfully harvested.
			print("\nThere are "+str(len(successful_AuthIDs_ARRAY))+" records in successful_AuthIDs_ARRAY.")
			print("\nThere are "+str(len(problem_AuthIDs_ARRAY))+" records in problem_AuthIDs_ARRAY!!!\n")
			
			stringToWrite = "\nThere are "+str(len(successful_AuthIDs_ARRAY))+" records in successful_AuthIDs_ARRAY"
			write_to_file(filename,stringToWrite)			
			stringToWrite = "There are "+str(len(problem_AuthIDs_ARRAY))+" records in problem_AuthIDs_ARRAY!!!\n"
			write_to_file(filename,stringToWrite)
			
			if(len(missedAuthIDs) > 0):
				print("There are "+str(len(missedAuthIDs))+" AuthID(s) missing in BOTH successful_AuthIDs_ARRAY and problem_AuthIDs_ARRAY that are in AuthID_LIST!!!")
				print("These will be added to problem_AuthIDs_ARRAY")
				
				stringToWrite = "There are "+str(len(missedAuthIDs))+" AuthID(s) missing in BOTH successful_AuthIDs_ARRAY and problem_AuthIDs_ARRAY that are in AuthID_LIST!!!\n\tThese will be added to problem_AuthIDs_ARRAY\n"
				write_to_file(filename,stringToWrite)
				
				problem_AuthIDs_ARRAY = problem_AuthIDs_ARRAY + missedAuthIDs
				
	elif processFlagCount == 2: ## second-pass data write if pAuthID_array has records
		print("\nTried to reprocess "+str(len(problem_AuthIDs_ARRAY))+" records in problem_AuthIDs_ARRAY.\n")
		print("\n\tThere were "+str(len(unique_problem_AuthIDs_ARRAY))+" UNIQUE records in unique_problem_AuthIDs_ARRAY.\n")
		#print("\nThere were "+str(len(unique_successful_AuthIDs_ARRAY))+" records in unique_successful_AuthIDs_ARRAY.\n")
		
		stringToWrite = "\nThere were "+str(len(successful_AuthIDs_ARRAY))+" records in successful_AuthIDs_ARRAY ("+str(len(unique_successful_AuthIDs_ARRAY))+" were UNIQUE records)." ## -1 to ignore "Trying to re-process problem AuthIDs" text (THIS HAS BEEN MUTED NOW)
		write_to_file(filename,stringToWrite)		
		stringToWrite = "\nTried to REPROCESS the "+str(len(problem_AuthIDs_ARRAY))+" records in problem_AuthIDs_ARRAY ("+str(len(unique_problem_AuthIDs_ARRAY))+" were UNIQUE records)." ## -1 to ignore "Trying to re-process problem AuthIDs" text (THIS HAS BEEN MUTED NOW)
		write_to_file(filename,stringToWrite)
		stringToWrite = "\nThere are now "+str(len(successful_AuthIDs_ARRAY2))+" recovered records in successful_AuthIDs_ARRAY2 ("+str(len(unique_successful_AuthIDs_ARRAY2))+" are UNIQUE records)."
		write_to_file(filename,stringToWrite)
		
		for AuthID in AuthID_LIST:
			if ((AuthID != 'Trying to re-process problem AuthIDs (if any)') ## ignore "Trying to re-process problem AuthIDs" text
				and (AuthID not in successful_AuthIDs_ARRAY2) and (AuthID not in successful_AuthIDs_ARRAY)): ## if AuthID is missing in BOTH successful_AuthIDs_ARRAYs
				#print("AuthID left unprocessed after re-processing: "+str(AuthID)) ## muted because too texty
				problem_AuthIDs_ARRAY2.append(AuthID)
				
		global unique_problem_AuthIDs_ARRAY2
		unique_problem_AuthIDs_ARRAY2 = uniquify_Array(problem_AuthIDs_ARRAY2)
				
		if (len(unique_problem_AuthIDs_ARRAY2) > 0):
			print("Data could not be harvested for "+str(len(unique_problem_AuthIDs_ARRAY2))+" unique AuthIDs")
			print("These AuthIDs will be written.")
			stringToWrite = "\nThere are "+str(len(problem_AuthIDs_ARRAY2))+" illegal(?) AuthIDs in problem_AuthIDs_ARRAY2 ("+str(len(unique_problem_AuthIDs_ARRAY2))+" are UNIQUE records).\n"
			write_to_file(filename,stringToWrite)
			
			print_and_write_ArrayDataContents(problem_AuthIDs_ARRAY2,'problem_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
			print_and_write_ArrayDataContents(unique_problem_AuthIDs_ARRAY2,'#unique_problem_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
			
		else:
			print("All "+str(len(AuthID_LIST))+" AuthID data have been successfully harvested!!!")
			stringToWrite = "\nAll "+str(len(AuthID_LIST))+" AuthID data have been successfully harvested!!!\n"
			write_to_file(filename,stringToWrite)
			
		if (len(missedAuthIDs) > 0):
			print("There are "+str(len(missedAuthIDs))+" NEW AuthID(s) missing in BOTH successful_AuthIDs_ARRAY and problem_AuthIDs_ARRAY that are in AuthID_LIST!!!")
			print("This should NOT happen. Contents of this array will be written.")
			
			stringToWrite = "\nThere are "+str(len(missedAuthIDs))+" NEW AuthID(s) missing in BOTH successful_AuthIDs_ARRAY and problem_AuthIDs_ARRAY that are in AuthID_LIST!!!\n\tThis should NOT happen. Contents of this array will be written\n"
			write_to_file(filename,stringToWrite)
			print_and_write_ArrayDataContents(missedAuthIDs,arrayName="missedAuthIDs",toPrint=0,toWrite=1)
			
		stringToWrite = "\nThere were "+str(len(UNIQUE_DATA_WRITTEN_TO_CSV))+" UNIQUE records written to DATA_WRITTEN_TO_CSV file ("+str(len(DATA_WRITTEN_TO_CSV))+" were non-unique records)."
		write_to_file(filename,stringToWrite)
		
	else: ## processFlagCount is neither 1 nor 2 - THIS MUST NOT HAPPEN!!!
		print("Illegal processFlagCount encountered: "+str(processFlagCount))
		
		stringToWrite = "\n\nIllegal processFlagCount encountered: "+str(processFlagCount)
		write_to_file(filename,stringToWrite)
		
	return;

## This function writes the AuthID_***_ARRAY contents to respective files if there are valid contents.
## Also writes the count of items written to "#final_summary_AuthIDs.txt".
## NOTE, there are repetitions in code. Ideally, want to optimise coding by incorporating a FOR loop...
def write_AuthID_OTHERLIST_ARRAY_to_CSV():
	filename = "#final_summary_AuthIDs.txt"
	
	global AUTHID_NAME_VARIATIONS_ARRAY
	
	#AUTHID_NAME_VARIATIONS_ARRAY = uniquify_Array(AUTHID_NAME_VARIATIONS_ARRAY)
	
	if len(AUTHID_NAME_VARIATIONS_ARRAY) > 0:
		header3 = ['AuthID','AuthorSurname','AuthorGivenName','AuthorInitials','AuthorNameType']
		#print_and_write_ArrayDataContents(AUTHID_NAME_VARIATIONS_ARRAY,'AUTHID_NAME_VARIATIONS_ARRAY',toPrint=0,toWrite=1)
		AUTHID_NAME_VARIATIONS_ARRAY = uniquify_Array(AUTHID_NAME_VARIATIONS_ARRAY)
		
		with open('##AUTHID_NAME_VARIATIONS_ARRAY.csv', 'w', newline='',encoding='utf-8') as csvfile3: ## Open the csv file------------------1
			csvwriter3 = csv.writer(csvfile3, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
			write_data_to_CSV(csvwriter3,header3) ##write HEADER ONCE
			print("\nWriting csvfile3: AUTHID_NAME_VARIATIONS_ARRAY...")
			for i in range(0,len(AUTHID_NAME_VARIATIONS_ARRAY)):
				processedData_array3 = AUTHID_NAME_VARIATIONS_ARRAY[i]
				write_data_to_CSV(csvwriter3,processedData_array3)
			print("\nFinished writing csvfile3: AUTHID_NAME_VARIATIONS_ARRAY")
			csvfile3.close() ## Close csv-------------------------4
			
		stringToWrite = "\nThere were "+str(len(AUTHID_NAME_VARIATIONS_ARRAY))+" records written to AUTHID_NAME_VARIATIONS_ARRAY file."
		write_to_file(filename,stringToWrite)
		
	return;

def finalise_validaton_and_logfiles(csvwriter, argumentValues):
	
	file_to_write = "check_processed_records_from_all_AuthID.txt"
	stringToWrite = "stats BEFORE reprocess:\n Total AuthIDs processed = "+str(AuthID_COUNTER)+", Total AuthIDs in File = "+str(AuthIDS_IN_FILE)+", Difference = "+str(AuthIDS_IN_FILE - AuthID_COUNTER)
	write_to_file(file_to_write,stringToWrite)
	
	processFlagCount = 1 ## typical first-pass data write as long as there are some data written to file (i.e. AuthID_COUNTER > 0)
	write_final_summary_AuthIDs_File(processFlagCount)
	
	global unique_problem_AuthIDs_ARRAY
	unique_problem_AuthIDs_ARRAY = uniquify_Array(problem_AuthIDs_ARRAY)
	global unique_successful_AuthIDs_ARRAY
	unique_successful_AuthIDs_ARRAY = uniquify_Array(successful_AuthIDs_ARRAY)
	
	length_of_unique_pAuthID_array = len(unique_problem_AuthIDs_ARRAY)
	if length_of_unique_pAuthID_array > 0: ## do this ONLY if there are problem AuthIDs stored from various exceptions and mismatch errors
		processFlagCount = 2 ## set processFlagCount to 2 for second-pass data write
		print("\n\nNumber of UNIQUE records in unique_problem_AuthIDs_ARRAY = "+str(length_of_unique_pAuthID_array))
		print("------Trying to re-process problem AuthIDs------\n")
		#problem_AuthIDs_ARRAY.append("Trying to re-process problem AuthIDs (if any)") ## this entry might cause an unknown error - just ignore it
		#successful_AuthIDs_ARRAY.append("Trying to re-process problem AuthIDs (if any)")
		
		recoveredAuthIDs = 0 ## reset to zero to reflect recovered AuthIDs by unique_problem_AuthIDs_ARRAY
		recoveredAuthIDs2 = 0 ## reset to zero to reflect recovered AuthIDs by problem_URL_ARRAY2
		print("Attempting to recover using unique_problem_AuthIDs_ARRAY")
		recoveredAuthIDs = iterate_through_AuthID_list_file_and_write_data(argumentValues,csvwriter,unique_problem_AuthIDs_ARRAY,reprocessTag = 'Y',suppliedURL='')
		print("recoveredAuthIDs using unique_problem_AuthIDs_ARRAY: "+str(recoveredAuthIDs))
		
		filename = "#final_summary_AuthIDs.txt"
		stringToWrite = "\nRecoveredAuthIDs from unique_problem_AuthIDs_ARRAY: "+str(recoveredAuthIDs)
		write_to_file(filename,stringToWrite)
		
		global unique_problem_URL_ARRAY2
		unique_problem_URL_ARRAY2 = uniquify_Array(problem_URL_ARRAY2)
		len_unique_problem_URL_ARRAY2 = len(unique_problem_URL_ARRAY2)
		if len_unique_problem_URL_ARRAY2 > 0:
			print("Attempting to recover using problem_URL_ARRAY2")
			AuthID_List_to_Process = ''
			totalProcessedAuthIDs = 0
			
			for i in range(0,len_unique_problem_URL_ARRAY2):
				suppliedURL = unique_problem_URL_ARRAY2[i]
				recAuthIDs2 = process_AuthID_data(csvwriter,AuthID_List_to_Process,argumentValues,totalProcessedAuthIDs,suppliedURL,reprocessTag='Y')
				totalProcessedAuthIDs = totalProcessedAuthIDs + recAuthIDs2
				recoveredAuthIDs2 = recoveredAuthIDs2 + recAuthIDs2
				
			print("recoveredAuthIDs using problem_URL_ARRAY2: "+str(recoveredAuthIDs2))
			filename = "#final_summary_AuthIDs.txt"
			stringToWrite = "RecoveredAuthIDs from problem_URL_ARRAY2: "+str(recoveredAuthIDs2)+"\n"
			write_to_file(filename,stringToWrite)
		
		recoveredAuthIDs = recoveredAuthIDs + recoveredAuthIDs2
		print("\n\nSUCCESSFULLY RECOVERED "+str(recoveredAuthIDs)+" RE-PROCESSED AuthIDs")
		
	if len(unique_successful_AuthIDs_ARRAY) > 0: ## this is generally the case. Print and write the array contents IRRESPECTIVE of pAuthID_array but ONLY if there are successful AuthIDs. 
		print_and_write_ArrayDataContents(problem_AuthIDs_ARRAY,'problem_AuthIDs_ARRAY',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(unique_problem_AuthIDs_ARRAY,'#unique_problem_AuthIDs_ARRAY',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(successful_AuthIDs_ARRAY,'successful_AuthIDs_ARRAY',toPrint=0,toWrite=1) ## this is too large may not very useful.
		# #file_name = str(len(successful_AuthIDs_ARRAY))+"_successful_URL_ARRAY.txt"
		# #stringToWrite = "There are "+str(len(successful_AuthIDs_ARRAY))+" non-unique successful AuthIDs.\nThese are not printed here because the list and file is too large and not very useful."
		# #write_to_file(file_name,stringToWrite)
		print_and_write_ArrayDataContents(unique_successful_AuthIDs_ARRAY,'unique_successful_AuthIDs_ARRAY',toPrint=0,toWrite=1)
		
		## The following has been moved to write_final_summary_AuthIDs_File(processFlagCount =2)
		# global unique_problem_AuthIDs_ARRAY2
		# unique_problem_AuthIDs_ARRAY2 = uniquify_Array(problem_AuthIDs_ARRAY2)
		# print_and_write_ArrayDataContents(problem_AuthIDs_ARRAY2,'problem_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
		# print_and_write_ArrayDataContents(unique_problem_AuthIDs_ARRAY2,'unique_problem_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
		
		global unique_successful_AuthIDs_ARRAY2
		unique_successful_AuthIDs_ARRAY2 = uniquify_Array(successful_AuthIDs_ARRAY2)
		print_and_write_ArrayDataContents(successful_AuthIDs_ARRAY2,'successful_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
		print_and_write_ArrayDataContents(unique_successful_AuthIDs_ARRAY2,'unique_successful_AuthIDs_ARRAY2',toPrint=0,toWrite=1)
		
	if processFlagCount == 2: ## this is ONLY true if pAuthID_array had any records
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
			
		write_final_summary_AuthIDs_File(processFlagCount)
		
	write_AuthID_OTHERLIST_ARRAY_to_CSV() ## this is done at the end irrespective of processFlagCount value
	
	file_to_write = "check_processed_records_from_all_AuthID.txt"
	stringToWrite = "stats AFTER reprocess:\n Final AuthIDs processed = "+str(AuthID_COUNTER)+", Total AuthIDs in File = "+str(AuthIDS_IN_FILE)+", Difference = "+str(AuthIDS_IN_FILE - AuthID_COUNTER)
	write_to_file(file_to_write,stringToWrite)
	
	return;

def MAIN_AuthID():
	filename_location = select_file_and_initiate_variables() ## retreives the location of the user-selected AuthID list
	
	argumentValues = ['APIkey', 'encodingFormat'] ## defining an array of TWO elements that will contain the values for the API key and other related arguments
	argumentValues = getArgumentValues()
	
	print('\nAuthID list located in: '+str(filename_location))
	print('\nThere are '+str(AuthIDS_IN_FILE)+' AuthIDs in the file')
	
	filename = "#final_summary_AuthIDs.txt"
	stringToWrite = "File of AuthIDs located in: "+str(filename_location)+"\n"
	write_to_file(filename,stringToWrite)
	
	with open('#AuthorRecords_from_AuthID_List_' + time.strftime("%d%m%Y-%H%M") + '.csv', 'w', newline='',encoding=defaultEncodingFormat) as csvfile: ## Open the csv file------------------1
		csvwriter = csv.writer(csvfile, delimiter=',') ## Open the csv writer-------------------------------------------------------------2
		print("\nINITIATING CSV data file to write...")
		
		header = generate_header(csvwriter,suppliedHeader='') ## write header ONCE
		#print (header)
		print("\nHEADER written to file.")
		print("Writing DATA (if exists)...\n")
		
		supplied_AuthID_List = []
		AuthIDcount = iterate_through_AuthID_list_file_and_write_data(argumentValues,csvwriter,supplied_AuthID_List,reprocessTag='N',suppliedURL='')
		
		if AuthIDcount == 0: ## no AuthID data in file. Exit directly.
			print("\nWarning: number of AuthIDs = "+str(AuthIDcount)+". No data has been written to file!!!")
			
			stringToWrite = "\nWarning: number of AuthIDs = "+str(AuthIDcount)+" (ZERO). No data has been written to file!!!"
			write_to_file(filename,stringToWrite)
			
		else: ## write final summary, validate and re-process problem AuthIDs if needed
			finalise_validaton_and_logfiles(csvwriter,argumentValues)
			
		print("\n\nThe API key has been used "+str(API_KEY_USAGE)+ " times for this exercise.\n")
		
		stringToWrite = "\n\nDetails from 'check_processed_records_from_all_AuthID.txt':\n"
		write_to_file(filename,stringToWrite)
		
		## the following copies the final summary from check_processed_records_from_all_AuthID.txt and writes to #final_summary_AuthIDs.txt
		with open('check_processed_records_from_all_AuthID.txt') as source_file:
			with open (filename, 'a') as sink_file:
				for line in source_file:
					if len(line) > 10 and '========' not in line: ## the AuthorID is prefixed with "AUTHOR_ID:" (len = 10)
						#print("len(line): "+str(len(line)))
						sink_file.write('\t'+line)
						
		stringToWrite = "\n\nThe API key has been used "+str(API_KEY_USAGE)+ " times for this exercise.\n"
		write_to_file(filename,stringToWrite)
		
		# print("The following ARRAYS are written optionally (program may crash if unicode error encountered):")
		# print_and_write_ArrayDataContents(AUTHID_NAME_VARIATIONS_ARRAY,'AUTHID_NAME_VARIATIONS_ARRAY',toPrint=0,toWrite=1)
		
		print("\nNow EXITTING")
		csvfile.close() ## Close csv-------------------------4
		print("	Publications data CSV file CLOSED")
		return;


MAIN_AuthID()

##=============================================================###
## BELOW IS THE WORKTHROUGH PROTOCOL WHILE CREATING THIS SCRIPT	##
## FOR RECORDS ONLY												##
##=============================================================###
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=
	# #change to mainAuthID. DONE
	# #need to modify global Vars related to EIDs. DONE
	# #only keep minimum. DONE
	# #?defaultItemsPerPage? 25. DONE
	# #?viewEID? kept as a blank. DONE
	# #~?AuthID_AUTHORS_ARRAY? removed. DONE
	# #~?AuthID_FUNDERS_ARRAY? removed. DONE
	# #line 372-375: generating the au-id query needs work: [au-id() OR] DONE
	# ###AuthID_AFILLIATIONS_ARRAY Renamed to AuthID_NAME_VARIATIONS_ARRAY###. DONE
	# #need to expand on preffered name tag to extract the sub-tags (detailedTagPairs). needed a workaround for quick fix:
	# #	join main output with AuthID_NAME_VARIATIONS_ARRAY on AuthorID. DONE
	# #check outputFiles. DONE
	# ########<===========================&&&&&&&&&&&&&&&&&&&&&&&&&&&& CHECK THIS LOGIC

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=

# Most frequent function calls e.g. write_to_file(),validatedArraySize or print() are ignored
# ------------------------------------------------------------------------------------

# -mainAuthID
  # [select_file_and_initiate_variables]
  # [getArgumentValues]
  # -genHeader. DONE
	# -HEADER: AuthID, AuthPreferredName, ORCID, nameVariantList. DONE
	   # -START_END_TAGS_ARRAY must have SAME no. of cols/array/objValue PLUS 2 (totalResult, entry). DONE
	# [write_data_to_CSV]***(csvfile: HEADER)
  # -iterate_through_AuthID_list_file_and_write_data. DONE ####
  	# #[validatedArraySize] <---------------------------to confirm len_supplied_AuthID_List: 0 to ''
	# -process_AuthID_data'''{in a loop}'''. DONE
		# -generate_AuthID_URL. DONE
		# -output_from_URL. DONE
			# -[extract_xml_data]****: URL output:totalResults_array. DONE
		# #no [validatedArraySize] but a manual check is done after value returned from output_from_URL()
		# -create_AuthID_data_Array_of_array. DONE
			# [extract_xml_data]****: URL output:Entry_object_array
			# #[validatedArraySize] <-------------to confirm size_of_Entry_object_array: 0 to 26 CHECK THIS LOGIC: should be ''?
			# [extract_xml_data]****: EntryObj:cell_data_array(AuthID)'''{in a loop}'''
			# #[validatedArraySize] <-------------to confirm size_of_cell_data_array(AuthID): 0 to 2
			# -harvest_remaining_cell_data*******'''{in a loop}'''. DONE#(recursion_enabled = Y)#
				# [extract_xml_data]****: EntryObj:cell_data_array(nonAuthID)
				# #[validatedArraySize] <----to confirm size_of_cell_data_array(nonAuthID): -1 to ''
				# -format_cell_data ##SIMPLIFIED##. DONE
				# -process_multiple_data_value_list. DONE ##IF RECURSION ENABLED - this is true the first time##
				    # AuthorNameVariantList ##DEFINED##
					# [harvest_remaining_cell_data] #(recursion_enabled = N)#
				# -convert_multiple_data_array_to_stringList. DONE
					# [format_cell_data]
			# #[validatedArraySize] <-------to confirm exact match with HEADER: -1 to +1 len(HEADER)
		# [write_data_to_CSV]***(csvfile: FULL_DATA)
  # -finalise_validaton_and_logfiles ####
	# [write_final_summary_AuthIDs_File] #Flag = 1 ALWAYS#
		# [print_and_write_ArrayDataContents]
	# -iterate_through_AuthID_list_file_and_write_data
		# -process_AuthID_data'''{in a loop}'''
	# -process_AuthID_data'''{in a loop}'''
	# [print_and_write_ArrayDataContents]
	# [write_data_to_CSV]***(csvfile2: UNIQUE_DATA_WRITTEN_TO_CSV)'''{in a loop}'''
	# [write_final_summary_AuthIDs_File] #if Flag = 2#
	# [write_AuthID_OTHERLIST_ARRAY_to_CSV]
		# [write_data_to_CSV] #(multiple instances for headers and data if conditions are met)
	

# Note on splicing and weird pub counts
# 36151565900  99, 103xu
# 55794552800  99,103tracy
# 57117183300 3b,103nodata-
# 57200912820 3b,103nodata-
# 57203239068 3b,103nodata-
# 57203350683 3b,103nodata-
# 57207196969  99,103nomoto

# searching scopus with the 3b/103nodata AuIDs pull the '99' data!
# the splicing works, and somehow it allows pulling old data that 
# are now merged with updated record ... ALL IS WELL

# AuthID	AuthorPreferredName	AuthORCID	CurrentAffiliation	AuthorNameVariantList
# 57203575320	no AuthorPreferredName data available	no AuthorORCID data available	no CurrentAffiliation data available	no AuthorNameVariantList data available
# 57203350683	no AuthorPreferredName data available	no AuthorORCID data available	no CurrentAffiliation data available	no AuthorNameVariantList data available
# 57203239068	no AuthorPreferredName data available	no AuthorORCID data available	no CurrentAffiliation data available	no AuthorNameVariantList data available
# 57200912820	no AuthorPreferredName data available	no AuthorORCID data available	no CurrentAffiliation data available	no AuthorNameVariantList data available
# 57117183300	no AuthorPreferredName data available	no AuthorORCID data available	no CurrentAffiliation data available	no AuthorNameVariantList data available