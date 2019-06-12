import json
import os
import sys
import re
import argparse
import sqlparse
import random
from collections import Counter 


# Helper function

EXIST_TABLES = ["academic", "geo", "imdb", "restaurants", "scholar", "yelp"]
EXIST_SQL_COUNT = 0
EXIST_Q_COUNT = 0
OUR_SQL_COUNT = 0
OUR_Q_COUNT = 0

VALUE_NUM_SYMBOL = 'VALUE'
    
def strip_query(query,columnNames,tableNames):
    '''
    return keywords of sql query
    '''
    query_keywords = []
    query = query.strip().replace(";","").replace("\t","")
    query = query.replace("(", " ( ").replace(")", " ) ")
    query = query.replace(">=", " >= ").replace("=", " = ").replace("<=", " <= ").replace("!=", " != ")


    # then replace all stuff enclosed by "" with a numerical value to get it marked as {VALUE}
    str_1 = re.findall("\"[^\"]*\"", query)
    str_2 = re.findall("\'[^\']*\'", query)
    values = str_1 + str_2
    for val in values:
        query = query.replace(val.strip(), VALUE_NUM_SYMBOL)

    query_tokenized = query.split()
    float_nums = re.findall("[-+]?\d*\.\d+", query)
    
    query_tokenized = [VALUE_NUM_SYMBOL if qt in float_nums else qt for qt in query_tokenized]
    query = " ".join(query_tokenized)
    int_nums = [i.strip() for i in re.findall("[^tT]\d+", query)]

    
    query_tokenized = [VALUE_NUM_SYMBOL if qt in int_nums else qt for qt in query_tokenized]
    # print int_nums, query, query_tokenized

    for tok in query_tokenized:
        if "." in tok:
            table = re.findall("[Tt]\d+\.", tok)
            if len(table)>0:
                to = tok.replace(".", " . ").split()
                to = [t.lower() for t in to if len(t)>0]
                query_keywords.extend(to)
            else:
                query_keywords.append(tok.lower())

        elif len(tok) > 0:
            if tok in columnNames:
                query_keywords.append("column0")
            elif tok in tableNames:
                query_keywords.append("table0")
            else:
                query_keywords.append(tok.lower())

    return query_keywords

def replace_values(sql,columnNames,tableNames):
    sql = sqlparse.format(sql, reindent=False, keyword_case='upper')
    sql = re.sub(r"(<=|>=|=|<|>|,)",r" \1 ",sql)
    sql = re.sub(r"(T\d+\.)\s",r"\1",sql)
    query_toks_no_value = strip_query(sql,columnNames,tableNames)
    return query_toks_no_value


def findAllNames(tables):
    columnNames = set()
    tableNames = set()
    for table in tables:
        for table_name in table['table_names_original']:
            tableNames.add(table_name)
        for column_name in table['column_names_original']:
            columnNames.add(column_name[1])
    return columnNames,tableNames

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True,help="An input file that contains coseql data same format as spider.")
    parser.add_argument("--tables", default="tables.json",help="A file that contains names of tables and columns of each database.")
    args = parser.parse_args()

    in_filename = args.input
    table_filename = args.tables

    with open(in_filename, 'r') as infile:
        in_dialogs = json.load(infile)
    with open(table_filename,'r') as infile:
        tables = json.load(infile)

    columnNames,tableNames = findAllNames(tables)
    dataset = [" ".join(replace_values(entry["query"],columnNames,tableNames)) for entry in in_dialogs]
    counter = Counter(dataset)
    print counter.most_common(60)





