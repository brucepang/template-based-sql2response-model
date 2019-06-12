import json
import os
import sys
import re
import math
import argparse
import traceback
import sqlite3
import sqlparse
import random
from os import listdir, makedirs
from collections import OrderedDict,defaultdict
from nltk import word_tokenize, tokenize
from os.path import isfile, isdir, join, split, exists, splitext
from collections import Counter 
from utils import *


def constructNameMapping(tables):
    nameMap = dict()
    for table in tables:
        db_id = table["db_id"]
        nameMap[db_id] = dict()
        nameMap[db_id]['table'] = defaultdict(str)
        tableNameMapping = nameMap[db_id]['table']
        for i in range(len(table['table_names'])):
            tableNameMapping[table['table_names_original'][i].lower()] = table['table_names'][i].lower()
        nameMap[db_id]['column'] = defaultdict(str)
        columnNameMapping = nameMap[db_id]['column']
        for i in range(len(table['column_names'])):
            columnNameMapping[table['column_names_original'][i][1].lower()] = table['column_names'][i][1].lower()
        
    return nameMap


# Find the template that best fit in the sql statement

def match(sql,templates):
    aggregate = set(["count","max","min","avg","sum"])
    comparison = set([">","<",">=","<=","!=","=",'like'])
    logic = set(["and,or"])
    tableLogic = set(["union","intersect","except"])
    max_match = float("-inf")
    candidate = templates[0]["SQL Pattern"]
    sql, _ = replace_values(sql)
    sql = mergeComparison(sql)
    for template in templates:
#         tokenized_template = [token.lower() for token in re.split(" |{|}|,",template["SQL Pattern"]) if token]
        tokenized_template, _ = replace_values(template["SQL Pattern"])
        # merge all aggregates function and comparison
        for i,token in enumerate(tokenized_template):
            if token[:-1] == "aggregate":
                tokenized_template[i] = "aggregate"
            if token[:-1] == "comparison":
                tokenized_template[i] = "comparison"
            if token[:-1] == "logic":
                tokenized_template[i] = "logic"
                
        template_map = Counter(tokenized_template)
        sql_cp = list(sql)
        for i in range(len(sql_cp)):
            if sql_cp[i] in aggregate:
                sql_cp[i] = "aggregate"
            if sql_cp[i] in comparison:
                sql_cp[i] = "comparison"
            if sql_cp[i] in logic:
                sql_cp[i] = "logic"
        
        sql_map = Counter(sql_cp)
        match = -abs(len(tokenized_template)-len(sql_cp))
        for component in sql_map:
            match+=min(sql_map[component],template_map[component]) - abs(sql_map[component]-template_map[component])
        if match > max_match:
            max_match = match
            candidate = template
    return candidate


# Generate a natural language response using the sql statement and a template
def generateResponse(sql,template,tables):
    tokenized_sql, values = replace_values(sql[0])
    tokenized_sql = mergeComparison(tokenized_sql)
    aggMap = {'avg':'average','max':'maximum','min':'minimum','count':'number of','sum':'total'}
    comparisonMap = {'>':'larger than','<':'smaller than','<=':'smaller than','>=':'larger than','=':'equal to','!=':'not equal to','like':'containing'}
    logicMap = {'and':'and','or':'or'}
    aggCt,compCt,logicCt,columnCt,tableCt,valueCt = 0,0,0,0,0,0
    nameMap = dict()
    tableMapping = tables[sql[2]]
    tableAliasMap = dict()
    
    #  map table short cuts like t1,t2,t3 to their table names
    for i,item in enumerate(tokenized_sql):
        if item == 'as':
            tableAliasMap[tokenized_sql[i+1]] = tokenized_sql[i-1]
    
    mapped = set()
    #  add results_map to our name map from training data
    if sql[1]:
        for key,val in sql[1].items():
            nameMap[key] = val
    # Fill each none SQL component slots with correct colomn/table name or value
    for i,component in enumerate(tokenized_sql):
        if component in aggMap:
            nameMap["aggregate"+str(aggCt)] = aggMap[component]
            aggCt += 1
            
        elif component in logicMap:
            nameMap["logic"+str(logicCt)] = logicMap[component]
            logicCt += 1
            
        elif component in comparisonMap:
            if tokenized_sql[i+1] in ['value','(']:
                nameMap["comparison"+str(compCt)] = comparisonMap[component]
                compCt += 1
            
        elif component == "value":    
            nameMap["value"+str(valueCt)] = values[valueCt]
            valueCt += 1
                
        # If component is not in the template, which means it is a specific name of column or table.
        elif component not in template["SQL Pattern"].lower():
            # check if the component has already been mapped
            if component in mapped:
                continue
            # if the previous token in from, it is likely to be a table name.
            elif tokenized_sql[i-1] in ["from","join"]:
                nameMap["table"+str(tableCt)] = tableMapping['table'][component]
                tableCt += 1
            # if the token is a column name
            else:
                columnName = "everything" if component == "*" else tableMapping['column'][component]
                nameMap["column"+str(columnCt)] = columnName
                columnCt += 1

    pattern = template["Response Pattern Plural"] if ("Response Pattern Plural" in template and not sql[1]) else template["Response Pattern"]
    tokens = pattern.split()
    for i in range(len(tokens)):
        if tokens[i] in nameMap:
            tokens[i] = nameMap[tokens[i]]
    return " ".join(tokens)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True,help="An input file that contains coseql data same format as spider.")
    parser.add_argument("--template", required=True,help="A template file.")
    parser.add_argument("--tables", default="tables.json",help="A file that contains names of tables and columns of each database.")
    args = parser.parse_args()

    in_filename = args.input
    template_filename = args.template
    table_filename = args.tables

    with open(in_filename, 'r') as infile:
        in_dialogs = json.load(infile)
    with open(template_filename, 'r') as infile:
        templates = json.load(infile)    
    with open(table_filename,'r') as infile:
        tables = json.load(infile)

    tables = constructNameMapping(tables)

    dataset = [(entry["query"],entry["results_map"],entry["database_id"],entry["response"]) for entry in in_dialogs]


    correct = 0
    output = []
    to_fix = []
    default = "Here is the item of the table ."
    for i in range(len(dataset)):
        if i % 100 == 0:
            print i
        data = dataset[i]
        template = match(data[0],templates)
        try:
            result = generateResponse(data,template,tables)
            output.append(data[3]+"\t"+result)
            correct += 1
        except:
            output.append(data[3]+"\t"+default)
            print "error"
            to_fix.append((dataset[i],i))
    print correct*1.0/len(dataset)


    f = open("template_output.txt", "w")
    for o in output:
        f.write(o.encode('utf8')+"\n")

