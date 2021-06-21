#!/usr/bin/env python3
"""Imports events exported from Mac Outlook calendar into a spreadsheet so
they can be filtered and uploaded into the NIF reporting tool.

To export events make sure you are using the old version of Mac Outlook and
go to File > Export and select "calendar" items to export. This will save a OLM
file, which you should provide as the input to this script <not 

"""
import os.path
import argparse
from datetime import datetime
import csv
import xml.etree.ElementTree as ET
import pytz
from zipfile import ZipFile
from tempfile import mkdtemp, tempdir


utc_tz = pytz.timezone('UTC')
sydney_tz = pytz.timezone('Australia/Sydney')


OUTPUT_CSV_HEADERS = [
    'Name of Engagement/Activity',
    'Engagement Start',
    'Engagement Finish',
    'Inviter',
    'Engagement Owner',
    'Engagement Owner ID',
    'Other relevant information',
    'Engagement Type',
    'Audience',
    'Abstract Submitted',
    'Abstract Submission Result',
    'Relevant Outcomes (Prizes, Awards, etc)',
    'Node Member Involved',
    'Participation Type',
    'Networking Type',
    'Additional Details or Comments',
    'Total Training Hours',
    'Users Trained',
    'Link to training Material',
    'Engagement Type, if Other',
    'Name of Tour Group',
    'Additional Comments',
    'Number in Group',
    'NIF-funded activity',
    'Engagement Description',
    'Role',
    'Role, if Other',
    'Partner',
    'Duration of Agreement',
    'Country',
    'Host Organisation',
    'On-going membership',
    'Group or Committee Name',
    'MoU/Agreement Objectives',
    'Meeting objectives and outcome',
    'Link, if applicable',
    'Committee objectives',
    'Consultation objectives and outcome',
    'Brief summary of outcomes',
    'Invited']


class Event():

    def __init__(self, title, start_date, end_date, inviter, attendees):
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.inviter = inviter
        self.attendees = set(attendees)


def convert_date(datestr):
    """Converts a datetime in the format exported from Outlook (Mac) into
    a Python datetime object in the Sydney timezone

    Parameters
    ----------
    datestr : str
        The string to convert in a custom datetime format

    Returns
    -------
    datetime.datetime
        A datetime object converted to Sydney timezone
    """
    dte = datetime.strptime(datestr, '%Y-%m-%dT%H:%M:%S')
    dte = utc_tz.localize(dte)
    dte = dte.astimezone(sydney_tz)
    return dte


parser = argparse.ArgumentParser()
parser.add_argument('input_file', help="The input OLM file to parse")
parser.add_argument('account_name', type=str,
                    help=(
                        "The name of the calendar account to use for the "
                        "import (e.g. 'Sydney Uni')"))
parser.add_argument('start_date',
                    help="The start date to import from (dd/mm/yy)")
parser.add_argument('end_date', help="The end date to import from (dd/mm/yy)")
parser.add_argument('output_file',
                    help="The output csv file to import into the NRT")
args = parser.parse_args()


tempdir = mkdtemp()

with ZipFile(args.input_file, 'r') as f:
   # Extract all the contents of zip file in current directory
   f.extractall(tempdir)

calendar_path = os.path.join(tempdir, 'Accounts', args.account_name, 
                            'Calendar', 'Calendar.xml')

with open(calendar_path) as f:
    try:
        tree = ET.parse(f)
    except:
        raise Exception(calendar_path + " couldn't parsed as XML")

root = tree.getroot()

period_start = datetime.strptime(args.start_date, '%d/%m/%y').astimezone()
period_end = datetime.strptime(args.end_date, '%d/%m/%y').astimezone()

events = {}
    
for appt in root.iter('appointment'):
    if appt.find('OPFCalendarEventCopySummary') is not None:
        title = appt.find('OPFCalendarEventCopySummary').text
    if appt.find('OPFCalendarEventCopyOrganizer') is not None:
        inviter = appt.find('OPFCalendarEventCopyOrganizer').text
    if appt.find('OPFCalendarEventCopyStartTime') is not None:
        start_date = convert_date(
            appt.find('OPFCalendarEventCopyStartTime').text)
    if appt.find('OPFCalendarEventCopyEndTime') is not None:
        end_date = convert_date(
            appt.find('OPFCalendarEventCopyEndTime').text)
    if appt.find('OPFCalendarEventCopyDescriptionPlain') is not None:
        desc = appt.find('OPFCalendarEventCopyDescriptionPlain').text
    attendees = []
    attendeeList = appt.find('OPFCalendarEventCopyAttendeeList')
    if attendeeList is not None:
        for attendee in attendeeList.findall('eventAttendee'):
            attendees.append(attendee.attrib['OPFCalendarAttendeeAddress'])

    if end_date < period_start or start_date > period_end:
        continue

    try:
        event = events[title]
    except KeyError:
        events[title] = Event(title, start_date, end_date, inviter, attendees)
    else:
        if start_date < event.start_date:
            event.start_date = start_date
        if end_date > event.end_date:
            event.end_date = end_date
        event.attendees.update(attendees)

with open(args.output_file, 'w') as csv_f:

    csv_writer = csv.DictWriter(csv_f, OUTPUT_CSV_HEADERS)

    csv_writer.writeheader()

    for event in events.values():
        row = {
            'Name of Engagement/Activity': event.title,
            'Engagement Start': event.start_date.strftime('%d/%m/%y'),
            'Engagement Finish': event.end_date.strftime('%d/%m/%y'),
            'Inviter': event.inviter,
            'Invited': ';'.join(event.attendees)}
        csv_writer.writerow(row)
