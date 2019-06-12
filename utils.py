import os
import sys
import re
import math
import traceback
import sqlite3
import sqlparse
import random

EXIST_TABLES = ["academic", "geo", "imdb", "restaurants", "scholar", "yelp"]
EXIST_SQL_COUNT = 0
EXIST_Q_COUNT = 0
OUR_SQL_COUNT = 0
OUR_Q_COUNT = 0

VALUE_NUM_SYMBOL = 'VALUE'

def find_values(sql):
    sql = sqlparse.format(sql, reindent=False, keyword_case='upper')
    sql = re.sub(r"(<=|>=|=|<|>|,)",r" \1 ",sql)
    sql = re.sub(r"(T\d+\.)\s",r"\1",sql)
    
    sql = sql.strip().replace(";","").replace("\t","")
    sql = sql.replace("(", " ( ").replace(")", " ) ")
    query = sql.replace(">=", " >= ").replace("=", " = ").replace("<=", " <= ").replace("!=", " != ")
    str_1 = re.findall("\"[^\"]*\"", query)
    str_2 = re.findall("\'[^\']*\'", query)
    values = str_1 + str_2
    return values
    
def strip_query(query):
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
    
    for qt in query_tokenized:
        if qt in float_nums:
            values.append(qt)
    
    query_tokenized = [VALUE_NUM_SYMBOL if qt in float_nums else qt for qt in query_tokenized]
    query = " ".join(query_tokenized)
    int_nums = [i.strip() for i in re.findall("[^tT]\d+", query)]
    
    for qt in query_tokenized:
        if qt in int_nums:
            values.append(qt)
    
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
            query_keywords.append(tok.lower())

    return query_keywords,values

def replace_values(sql):
    sql = sqlparse.format(sql, reindent=False, keyword_case='upper')
    sql = re.sub(r"(<=|>=|=|<|>|,)",r" \1 ",sql)
    sql = re.sub(r"(T\d+\.)\s",r"\1",sql)
    query_toks_no_value,values = strip_query(sql)

    return query_toks_no_value,values

def mergeComparison(tokenized_sql):
    for i in range(len(tokenized_sql)):
        if tokenized_sql[i] in ["<",">","!"] and tokenized_sql[i+1]=="=":
            tokenized_sql[i] += "="
            tokenized_sql[i+1] = ""
    return [token for token in tokenized_sql if token]
