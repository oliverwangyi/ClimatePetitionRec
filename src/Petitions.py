from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse
from selenium import webdriver
from pymongo import MongoClient
import time
import requests
import json
import simplejson
import re

# Crawling spider for Change.org Climate Change opened petitions
class ChangeSpider(BaseSpider):
    driver2 = webdriver.Firefox()

    name = "change_spider"
    allowed_domains = ['change.org']

    # Search by climate change
    start_urls = "https://www.change.org/search?q=" + "climate%20change"+"&offset="

    # Open URL in driver
    def __init__(self):
        self.driver = webdriver.Firefox()


    # Parse climate change petitions from search results starting from 1st page to last page and insert in database
    def parse(self, firstPage, lastPage):
        # open Mongodb local connection
        client = MongoClient('mongodb://localhost:27017/')
        collectionOpened = client.ClimateChange.Petition
        count = 0   #counter for the total number of petitions read so far

        # loop through the search result pages in range
        for pageCount in range(firstPage, lastPage):
            # set the offset parameter in URL
            url=self.start_urls+str((pageCount-1)*10)
            response = HtmlResponse(url)
            self.driver.get(response.url)

            # sleep 2 sec in order to finish loading the page HTML content and avoid being blocked form change.org
            # web server due to many requests in small time
            time.sleep(2)

            # loop through the petitions inside each page
            for itemCount in range(0, 9):
                try:
                    # sleep 0.1 sec to avoid being blocked form change.org
                    # web server due to many requests in small time
                    time.sleep(0.1)

                    ''' Get petition information

                    '''
                    # get the petition by xpath in the page layout
                    petition = self.driver.find_elements_by_xpath('// *[ @ id = "content"] / div / div / div / div / div / div[2] / ul / div[' + str(itemCount + 1) + '] / a')

                    # get the petition link
                    l = petition[0].get_attribute("href")

                    # check if the link is for a petition or something else
                    if '/p/' in l:
                        count += 1

                        # get petition id by URL through an http get request after setting change.org api key parameter
                        link = 'https://api.change.org/v1/petitions/get_id?petition_url=' + x + '&page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                        response = requests.get(link)

                        # load petition short details in json
                        results = json.loads(response.text)

                        # get petition id
                        petition_id = str(results["petition_id"])

                        # get all petition details by id through an http get request after setting change.org api key parameter
                        link = 'https://api.change.org/v1/petitions/' + petition_id + '?page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                        response = requests.get(link)
                        petitionDetails = response.text

                        # load all petition details in json to results
                        results = json.loads(response.text)
                        response = HtmlResponse(x)
                        self.driver2.get(response.url)
                        braclet = 1   # boolean to check if the } or not at the end of the json for appending new columns
                        try:
                            # crawling through css selectors to get (current number of supporters, total number of supporters needed to
                            # reach goal, and the goal number of supporters) that is not retrieved by change.org api

                            # get remaining number of supporters needed to reach the petition goal and goal number of supporters by css selector
                            supp = self.driver2.find_elements_by_css_selector('#content > div > div.container > div.row.mbxxl > div.js-petition-action-panel-container.col-xs-12.col-sm-4.xs-phn.xs-pbm.position-sticky.position-top > div > div > div > div > div.js-sign-and-share-components > div > div.type-s.type-weak > div.txt-r')
                            s=supp[0].text
                            goal = s[:s.index(' ')] # delete ',' from the goal number of supporters
                            goalNo = int(re.sub(',', '', goal)) # get the goal number of supporters in numbers
                            rem = s.rsplit(' ', 1)[1]   # get the remaining number of supporters to goal
                            remNo = int(re.sub(',', '', rem)) # delete ',' from the remaining number of supporters from goal in numbers
                            supporters=goalNo-remNo    # get the current number of supporters

                            # Append to json supporters numbers to all petition details into strIns which is the string
                            # that consolidates all petition, as well as the assiociated organizations, comments, updates and targets
                            # with this petition
                            strIns = petitionDetails[0:len(petitionDetails) - 1] + "," + '"supporters":' + '"' + str(supporters) + '",' + '"remaining_supporters":' + '"' + str(remNo) + '",' + '"needed_supporters":' + '"' + str(goalNo) + '",'
                            braclet = 0   # no }

                        # In case of failure to retrieve the supporters and goal numbers
                        except:
                            strIns = petitionDetails    #prepare strIns without supporters numbers

                        # For the sake of code tracing the sequence of reading is saved with the petition
                        if braclet == 1:  # Case there is a braclet remove the bracket and append the tracing sequence
                            strIns = strIns[0:len(strIns) - 1] + ',' + '"devTrace":' + '"' + str((pageCount-1)*10+itemCount) + '",'
                            braclet = 0
                        else:   # Case there is no bracket append the tracing sequence directly
                            strIns = strIns + '"devTrace":' + '"' + str((pageCount-1)*10+itemCount) + '",'

                        ''' Getting the associated Organizations with this petition if any

                        '''
                        organization_url = str(results["organization_url"])
                        if organization_url != "None":  # if there is organizations associated with this petition

                            # get orgnaization with organization url from petition data
                            link = 'https://api.change.org/v1/organizations/get_id?organization_url=' + organization_url + '&page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                            response = requests.get(link)   # get organization short description
                            data = json.loads(response.text)    # load organization short description as json
                            organization_id = str(data["organization_id"])  # get organization id

                            # Get organization details by organization id
                            link = 'https://api.change.org/v1/organizations/' + organization_id + '?page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                            response = requests.get(link)
                            org = response.text
                            strIns = strIns + org[1:len(org) - 1] + ',' # add organization details to conolidated petition data

                        ''' Get petition associated updates with this petition if any

                        '''
                        # Retreive associated updates with petition by petition id
                        link = 'https://api.change.org/v1/petitions/' + petition_id + '/updates?&page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                        response = requests.get(link)
                        data = json.loads(response.text)    # load updates as json
                        upd = simplejson.dumps(data['updates'], separators=(',', ':'))
                        if braclet == 1:    # if there is a braclet remove the braclet and append updates and number of updates
                            strIns = strIns[0:len(
                                strIns) - 1] + ',"updates":' + upd + ',' + '"updates_count":' + '"' + str(
                                len(data['updates'])) + '",'
                            braclet = 0
                        else:   # if there is no braclet directly append updates and number of updates
                            strIns = strIns + '"updates":' + upd + ',' + '"updates_count":' + '"' + str(
                                len(data['updates'])) + '",'

                        ''' Get associated users comments (reasons) with this petition if any

                        '''
                        # Retreive associated comments (reasons) with petition by petition id
                        link = 'https://api.change.org/v1/petitions/' + petition_id + '/reasons?&page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                        response = requests.get(link)
                        data = json.loads(response.text) # load comments  as json
                        rsn = simplejson.dumps(data['reasons'], separators=(',', ':'))

                        # Append comments and number of comments
                        strIns = strIns + '"reasons":' + rsn + ',' + '"reasons_count":' + '"' + str(
                            len(data['reasons'])) + '",'

                        ''' Get associated target authoroties, agencies or coporates that the petition addresses

                        '''
                        # Retreive associated targets with petition by petition id
                        link = 'https://api.change.org/v1/petitions/' + petition_id + '/targets?&page_size=1000&sort=time_desc&api_key=f7720f80ec4f67eeca1f6932d93069b92b627cc6ac6e5c95a18c89dc8a81792f'
                        response = requests.get(link)
                        data = json.loads(response.text)    # load targets as json
                        trg = simplejson.dumps(data, separators=(',', ':'))

                        # Append targets and number of targets
                        strIns = strIns + '"targets":' + trg + ',' + '"targets_count":' + '"' + str(
                            len(data)) + '"}'
                        # Parse the consolidated petitions and associated targets, comments, updates and organizations as json
                        DicIns = simplejson.loads('[%s]' % strIns)

                        # Insert open status petitions in database
                        if results["status"] == 'open':
                            collectionOpened.insert(DicIns)
                except: # case any exception then print petition
                    print l
        self.driver.close()


c = ChangeSpider()  # instantiate ChangeSpider crawler
c.parse(1,148)  # parse pages from upper to lower bound