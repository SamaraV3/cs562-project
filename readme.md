# CS562 Project Demo

This is code written by Samara Vassell and Isabella Baratta, written on top of the demo code created by nickmule77/cs562-project-demo:master.

**Note:** Don't forget to update the values in `.env` to match your environment.

## How to Run

1. Download dependencies:
   ```bash
   pip install -r requirements.txt
2. Run the generator
    * On Windows/Linux
    ```
    python generator.py input_query_file.txt
    ```
    * On Mac
    ```
    python3 generator.py input_query_file.txt
    ```

## Input Query Format
Create a text file with the following format
```
SELECT ATTRIBUTE(S):
cust, prod, 1_sum_quant, 2_avg_quant
NUMBER OF GROUPING VARIABLES(n):
2
GROUPING ATTRIBUTES(V):
cust, prod
F-VECT([F]):
1_sum_quant, 1_avg_quant
2_avg_quant
SELECT CONDITION-VECT([σ]):
1.state='NY'
2.state='NJ'
HAVING_CONDITION(G):
1_sum_quant > 50
```