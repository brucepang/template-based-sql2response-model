# Template-based sql2response Model

## Overview
We first create a list of SQL query patterns without values, column and table names that cover the most cases in the train set of CoSQL. 
And then we manually changed the patterns and their corresponding responses to make sure that table, column, and value slots in the responses have one-to-one map to the slots in the SQL query.
Once we have the SQL-response mapping list, during the prediction, new SQL statements are compared with every templates to find the best template to use. A score will be computed to represent the similarity between the SQL and each template.
The score is computed based on the number of each SQL key components existing in the SQL and each template. Components of the same types are grouped together to allow more flexible matching, like count, max, min are grouped to aggregate.

## Develop templates
**find_pattern.py** is the script that help find the most frequent patterns/templates among the dataset to insist users to choose templates efficiently.

`python find_pattern.py --input location_of_cosql_data --tables location_of_tables_file`

## Generate natural language response from SQL statement
**template_based.py** is the model file that takes in a template file, an input file, and a tables file. For each sql statement in the input file, it first matches it with a template based on our heuristic and then fills all slots in the template with values/names from the sql statement to generate the corresponding natural language response. If it fails, a default response will be generated.

`python template_based.py --input location_of_cosql_data --template location_of_template_file --tables location_of_tables_file`
