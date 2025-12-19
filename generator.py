import subprocess
import sys

#first things first: I need to read in a txt file with phi operator inputs

#cur = acc sales table btw

def parse_query_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    lines = content.strip().split('\n')
    S, n, V, F, o, G = [], 0, [], [], [], ""
    i = 0
    while i < len(lines):
        curr_line = lines[i].strip()
        if curr_line.startswith("SELECT ATTRIBUTE(S):"):
            #next line has acc attrs
            i += 1
            if i < len(lines):
                S_line = lines[i].strip()
                S = [attr.strip() for attr in S_line.split(",") if attr.strip()]
        elif curr_line.startswith("NUMBER OF GROUPING VARIABLES(n):"):
            #next line has n
            i += 1
            if i < len(lines):
                n = int(lines[i].strip())
        elif curr_line.startswith("GROUPING ATTRIBUTES(V):"):
            i += 1
            if i < len(lines):
                V_line = lines[i].strip()
                V = [attr.strip() for attr in V_line.split(",") if attr.strip()]
        elif curr_line.startswith("HAVING_CONDITION(G)"):
            i += 1
            if i < len(lines):
                G = lines[i].strip()
        elif curr_line.startswith("SELECT CONDITION-VECT"):
            #assume n is set at this point
            for _ in range(n):
                i += 1 #go to line of next grouping var
                temp = []
                if i < len(lines):
                    new_line = lines[i].strip()
                    temp = [attr.strip() for attr in new_line.split(",") if attr.strip()]
                    o.append(temp)
        elif curr_line.startswith("F-VECT([F]):"):
            #again, assume n is set at this point
            for _ in range(n):
                i += 1
                temp = []
                if i < len(lines):
                    new_line = lines[i].strip()
                    temp = [attr.strip() for attr in new_line.split(",") if attr.strip()]
                    F.append(temp)

        i += 1 #
    return S, n, V, F, o, G


def main():
    """
    This is the generator code. It should take in the MF structure and generate the code
    needed to run the query. That generated code should be saved to a 
    file (e.g. _generated.py) and then run.
    """
    
    #if there is no input file then ask for input from the cmd line
    if len(sys.argv) == 1:
        #read in from cmd line
        print("No input file provided. You get the honor of inputting the parameters manually")
        print("Input grouping variable aggregates as follows: number_aggfunc_attributename [ex: 1_sum_quant]")
        print("Input grouping variable attributes as follows: number.attributename [ex: 1.state]")
        #gather inputs
        S_input = input("S [format: val1, val2, ...]: ")
        S = [attr.strip() for attr in S_input.split(",")]
        n_input = input("N: ")
        n = int(n_input.strip())
        V_input = input("V [format: val1, val2, ...]: ")
        V = [attr.strip() for attr in V_input.split(",")]
        F_input = input("F [format: [1_agg_1, 1_agg_2], [2_agg_1, 2_agg_2], ...]: ")
        #first split by ,
        temp = F_input.split(",") #values still have brackets
        #then iterate over temp to create lists of lists in F
        F = []
        for val in temp:
            val = val.strip().strip('[').strip(']')
            agg_funcs = [agg.strip() for agg in val.split(",")]
            F.append(agg_funcs)
        o_input = input("o [format: [1_cond_1, 1_cond_2], [2_cond_1, 2_cond_2], ...]: ")
        temp = o_input.split(",") #values still have brackets
        o = []
        for val in temp:
            val = val.strip().strip('[').strip(']')
            conds = [cond.strip() for cond in val.split(",")]
            o.append(conds)
        G = input("G: ").strip()
    elif len(sys.argv) == 2: #they gave us a file
        S, n, V, F, o, G = parse_query_file(sys.argv[1])
    else:
        # Test MF Query with 2 grouping variables -> will eventually be read in
        S = ["cust", "prod", "1_sum_quant", "2_count_prod", "2_avg_quant"]  # SELECT
        n = 2  # 2 grouping variables
        V = ["cust", "prod"]  # GROUP BY cust
        F = [["1_sum_quant"], ["2_count_prod", "2_avg_quant"]]  # Aggregates for each GV
        o = [["1.state='NY'"], ["2.state='NJ'"]]  # Conditions for each GV
        G = "1_sum_quant > 50"  # HAVING

    #generates mf struct and related functions
    definitions = """
def check_condition(row, condition, grouping_var, entry=None):
    #check if row satisfies a condition for a grouping var
    if not condition or condition == "0": #no condition exists for this - assume we good
        return True
    #dont gotta worry abt ands and ors here
    condition_without_gv = condition.replace(f"{grouping_var}.", "", 1) #swap 1.state=NJ with state=NJ
    #lets allow the LIKE operator bcuz im nice like that
    if ' LIKE ' in condition_without_gv.upper():
        parts = re.split(' LIKE ', condition_without_gv, flags=re.IGNORECASE)
        if len(parts) != 2:
            return False
        left = parts[0].strip()
        right = parts[1].strip().strip("'\""")
        if left not in row:
            return False
        row_value = str(row[left]) #row[state] for example
        pattern = right #whatever darn regex we get smdh
        # Convert SQL LIKE pattern to regex: % -> .*, _ -> ., escape other special chars
        pattern = re.escape(pattern)
        pattern = pattern.replace('%', '.*').replace('_', '.')
        pattern = '^' + pattern + '$'

        return bool(re.match(pattern, row_value, re.IGNORECASE))

    operators = ['!=', '>=', '<=', '=', '>', '<'] #i rebuke the energy of any other operators
    for op in operators:
        if op in condition_without_gv:
            left, right = condition_without_gv.split(op, 1) #left=state, right=NJ
            left = left.strip()
            right = right.strip()

            #APPARENTLY this is where u can check if right side references a previous GV attr for emf **tba
            #pattern match for overall agg
            overall_pattern = r'^(sum|avg|count|max|min)_(\w+)$'
            all_dep = bool(re.match(overall_pattern, right))
            #pattern match to see if its dependent on an agg
            dep_patt = r"(\d+)_(sum|avg|min|max|count)_(\w+)$"
            is_dep = bool(re.match(dep_patt, right))
            #if it is then get value from entry 
            if is_dep or all_dep:
                right_ref = right
                right = entry.get(right_ref)
                #print(right)

            if left not in row:
                return False #attribute doesnt event exist IN the row
            row_value = row[left]

            #handle right side - if its quoted is a string
            if type(right) is str:
                right_value = right[1:-1] #remove quotes
                row_str = str(row_value)
                if op == '=':
                    return row_str == right_value
                elif op == '!=':
                    return row_str != right_value
                elif op in ['>', '>=', '<', '<=']:
                    #compare lexicographically
                    if op == '>':
                        return row_str > right_value
                    elif op == '>=':
                        return row_str >= right_value
                    elif op == '<':
                        return row_str < right_value
                    elif op == '<=':
                        return row_str <= right_value

            else:
                #try making it numeric
                try:
                    row_num = float(row_value) if row_value is not None else None
                    right_num = float(right)
                    
                    if row_num is None:
                        return False
                    
                    if op == '=':
                        return abs(row_num - right_num) < 0.000001 #deal with that floating point causing error
                    elif op == '!=':
                        return abs(row_num - right_num) < 0.000001
                    elif op == '>':
                        return row_num > right_num
                    elif op == '>=':
                        return row_num >= right_num
                    elif op == '<':
                        return row_num < right_num
                    elif op == '<=':
                        return row_num <= right_num
                    
                except (ValueError, TypeError):
                    #if if conversion failed i gotta treat them as strings instead
                    row_str = str(row_value)
                    right_str = str(right)
                    if op == '=':
                        return row_str == right_str
                    elif op == '!=':
                        return row_str != right_str
                    elif op == '>':
                        return row_str > right_str
                    elif op == '>=':
                        return row_str >= right_str
                    elif op == '<':
                        return row_str < right_str
                    elif op == '<=':
                        return row_str <= right_str

    return False #the input condition has eluded my capabilities

def evaluate_having(entry, having_condition):
    if not having_condition or having_condition == "0":
        return True
    condition_to_eval = having_condition #the entire statement including AND and OR and NOT
    
    # repl agg funcs -> 
    for key in entry.keys():
        if key.startswith(('1_', '2_', '3_', '4_', '5_', '6_', '7_', '8_', '9_')) and '_' in key[2:]:
            condition_to_eval = condition_to_eval.replace(key, f"entry['{key}']")
            #changes 1_sum_quant to entry[1_sum_quant]
    
    #now replace grouping attrs AND regular aggs
    for attr in entry.keys():
        if not attr.startswith(('1_', '2_', '3_', '4_', '5_', '6_', '7_', '8_', '9_')):
            condition_to_eval = condition_to_eval.replace(attr, f"entry['{attr}']")
            #changes cust to entry[cust]
    
    #lastly replace grouping var attributes like 1.quant
    for key in entry.keys():
        if key.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            condition_to_eval = condition_to_eval.replace(key, f"entry['{key}']")
            #changes 1.quant to entry[1.quant]
    try:
        return eval(condition_to_eval, {"entry": entry}) #python evals entry[1.quant] > 0 and entry[2_count_prod] == 1 :3
    except:
        return False

def get_select_values(entry, select_attrs):
    result = {}
    for attr in select_attrs:
        if attr in entry:
            # Direct attribute or aggregate
            result[attr] = entry[attr]
        elif '.' in attr:
            # Grouping variable attribute like "1.quant"
            gv_num, gv_attr = attr.split('.', 1)
            storage_key = f"gv_{gv_num}_{gv_attr}"
            if storage_key in entry:
                result[attr] = entry[storage_key]
            else:
                result[attr] = None
        else:
            result[attr] = None
    return result


class MFStruct:
    def __init__(self, proj_attrs, grouping_attrs, agg_func_set, pred_set, having_condition=""):
        self.proj_attrs = proj_attrs #S
        self.grouping_attrs = grouping_attrs #V
        #when we do generator.py im assuming this wont be created in the struct but done before passing all teh phi operators
        #but for testing purposes needs to be here rn
        #loop to determine if there are any grouping variable dependencies (EMF)
        for group in pred_set:
            for dependent in group:
                f_vect = agg_func_set
                #pattern to recognize if there is a dependency (gv agg is referenced)
                #split the left and right side
                for op in ["!=", ">=", "<=", "=", ">", "<"]:
                    if op in dependent:
                        left, right = dependent.split(op, 1)
                        left = left.strip()
                        rightd = right.strip()
                        #print(right)
                dep_patt = r"(\d+)_(sum|avg|min|max|count)_(\w+)$"
                is_dep = bool(re.match(dep_patt, rightd)) 
                #print(dependent)
                #is EMF and needs to be added to vector F
                if is_dep:
                    gvn = int(right.split('_', 1)[0])
                    #print(gvn)
                    if rightd not in f_vect[gvn-1]:
                        f_vect[gvn-1].append(rightd)
                    #print(f_vect)
            agg_func_set = f_vect
        self.all_agg_funcs = [item for sublist in agg_func_set for item in sublist] #F - list of lists
        self.pred_set = [item for sublist in pred_set for item in sublist] #o - list of lists
        self.entries = [] 
        #below allows attrs of grouping vars to be viewed
        self.gv_select_attrs = {}
        for attr in self.proj_attrs:
            if '.' in attr and not any(attr.startswith(f"{i}_") for i in range(1, 10)):
                # This is a grouping variable attribute like "1.quant" or "2.state"
                gv_num, gv_attr = attr.split('.', 1)
                if gv_num not in self.gv_select_attrs:
                    self.gv_select_attrs[gv_num] = []
                if gv_attr not in self.gv_select_attrs[gv_num]:
                    self.gv_select_attrs[gv_num].append(gv_attr)

        #and below checks for overall aggregates in SELECT
        #if its in HAVING then PERISH
        for attr in self.proj_attrs:
            #j how it looks
            overall_pattern = r'^(?!\d+_)(sum|avg|count|max|min)_(.+)$'  # count_quant
            match = re.match(overall_pattern, attr)
            if match:
                overall_agg = attr
                if overall_agg not in self.all_agg_funcs:
                    self.all_agg_funcs.append(overall_agg)
        #now store having condit
        self.having_condit = having_condition
        #split by AND/OR
        having_vals = re.split(r'(\bAND\b|\bOR\b)', having_condition)
        
        for val in having_vals: #assuming there is any lol
            val = val.strip()
            if any(op in val for op in ['!=', '>=', '<=', '=', '>', '<']):
                #split again to get left and right
                for op in ['!=', '>=', '<=', '=', '>', '<']:
                    if op in val:
                        left, right = val.split(op, 1)
                        left = left.strip()
                        right = right.strip()

                        #check both for overall aggs
                        for side in [left, right]:
                            if re.match(r'^(sum|avg|count|max|min)_\w+$', side) and side not in self.all_agg_funcs: #format of 'count_prod', etc
                                self.all_agg_funcs.append(side)
                                
            #overall agg dependency not already in select or having
            for group in pred_set:
            for dependent in group:
                #pattern to recognize if there is a dependency (gv agg is referenced)
                #split the left and right side
                for op in ["!=", ">=", "<=", "=", ">", "<"]:
                    if op in dependent:
                        left, right = dependent.split(op, 1)
                        left = left.strip()
                        rightd = right.strip()
                        #print(right)
                overall_pattern = r'^(sum|avg|count|max|min)_(.+)$' 
                is_dep = bool(re.match(overall_pattern, rightd)) 
                #print(dependent)
                #is EMF and needs to be added to vector F
                if is_dep:
                    if rightd not in self.all_agg_funcs:
                        self.all_agg_funcs.insert(0,rightd)
            

    def populate_entries(self, row):
        group_vals = {}
        for attr in self.grouping_attrs:
            group_vals[attr] = row[attr] #creates col for each grouping_attr + sets to row's acc value for entity
        
        #check if group alr exists
        for entry in self.entries:
            match = all(entry[attr] == group_vals[attr] for attr in self.grouping_attrs)
            if match:
                return entry #group alr exists - exit stage left
        
        new_entry = {}
        for attr in self.grouping_attrs:
            new_entry[attr] = row[attr] #j in case i mutate group_vals
        
        for agg_func in self.all_agg_funcs:
            # agg_func looks like "1_sum_quant", "2_avg_price", etc.
            # or sum_quant if we're unlucky
            if agg_func[0].isdigit():
                parts = agg_func.split('_')
                agg_type = parts[1]  # sum, avg, max, min, count
                
                if agg_type == "sum":
                    new_entry[agg_func] = 0
                elif agg_type == "count": 
                    new_entry[agg_func] = 0
                elif agg_type == "avg":
                    new_entry[agg_func] = 0.0
                    new_entry[f"{agg_func}_count"] = 0  # For avg computation -> 1_sum_quant_avg
                    new_entry[f"{agg_func}_sum"] = 0    # For avg computation
                elif agg_type == "max":
                    new_entry[agg_func] = None  # Will be set to first valid value
                elif agg_type == "min":
                    new_entry[agg_func] = None  # Will be set to first valid value
            else:
                parts = agg_func.split('_')
                if len(parts) == 2: #again count_quant, avg_quant, etc
                    agg_type = parts[0].strip() # avg in avg_quant
                    if agg_type == "sum":
                        new_entry[agg_func] = 0
                    elif agg_type == "count": 
                        new_entry[agg_func] = 0
                    elif agg_type == "avg":
                        new_entry[agg_func] = 0.0
                        new_entry[f"{agg_func}_count"] = 0
                        new_entry[f"{agg_func}_sum"] = 0
                    elif agg_type == "max":
                        new_entry[agg_func] = None
                    elif agg_type == "min":
                        new_entry[agg_func] = None
        
        #below for grouping attrs
        for gv_num, attrs in self.gv_select_attrs.items():
            for attr in attrs:
                storage_key = f"gv_{gv_num}_{attr}"
                new_entry[storage_key] = None
        
        self.entries.append(new_entry)
        return new_entry
        
    def update_aggregates(self, entry, gv_num, row):
        #first update overall aggs -> no GV condit, dif for loop
        for agg_func in self.all_agg_funcs:
            if not agg_func[0].isdigit() and gv_num=="0": #because i used 0 as a placeholder lol
                parts = agg_func.split('_') #  avg_quant becomes avg, quant
                if len(parts) == 2:
                    agg_type = parts[0] #sum, avg, etc
                    attr_name = parts[1] #col name
                    if attr_name not in row:
                        continue
                    if agg_type == "count" and row[attr_name] is not None:
                        entry[agg_func] = entry.get(agg_func, 0) + 1
                    else:
                        try:
                            value = float(row[attr_name])
                        except (ValueError, TypeError):
                            continue
                            
                        if agg_type == "sum":
                            entry[agg_func] = entry.get(agg_func, 0) + value
                        elif agg_type == "max":
                            if agg_func not in entry or entry[agg_func] is None or value > entry[agg_func]:
                                entry[agg_func] = value
                        elif agg_type == "min":
                            if agg_func not in entry or entry[agg_func] is None or value < entry[agg_func]:
                                entry[agg_func] = value
                        elif agg_type == "avg":
                            count_name = f"{agg_func}_count"
                            sum_name = f"{agg_func}_sum"
                            entry[count_name] = entry.get(count_name, 0) + 1
                            entry[sum_name] = entry.get(sum_name, 0) + value
                            if entry[count_name] > 0:
                                entry[agg_func] = entry[sum_name] / entry[count_name]
        
        for agg_func in self.all_agg_funcs:#iterate over all agg_funcs for gvs
            if agg_func.startswith(f"{gv_num}_"): #like 1_avg_quant, 2_count_prod, etc
                parts = agg_func.split('_') #will get ["1", "avg", "quant"]
                agg_type = parts[1] #"avg", "count", etc
                attr_name = '_'.join(parts[2:]) #SHOULD j be "quant", "prod", etc
                
                if attr_name not in row:
                    continue  # Skip if attribute doesn't exist in row

                if agg_type == "count" and row[attr_name] is not None:
                    entry[agg_func] += 1 #entry[2_cound_prod] += 1

                else: #if its type aint count
                    try:
                        value = float(row[attr_name])
                    except (ValueError, TypeError):
                        continue
                
                    if agg_type == "sum":
                        entry[agg_func] += value
                    elif agg_type == "max":
                        if entry[agg_func] is None or value > entry[agg_func]:
                            entry[agg_func] = value
                    elif agg_type == "min":
                        if entry[agg_func] is None or value < entry[agg_func]:
                            entry[agg_func] = value
                    elif agg_type == "avg":
                        count_name = f"{agg_func}_count"
                        sum_name = f"{agg_func}_sum"
                        entry[count_name] += 1
                        entry[sum_name] += value
                        if entry[count_name] > 0:
                            entry[agg_func] = entry[sum_name] / entry[count_name]
            
        self.update_gv_attributes(entry, gv_num, row)
    
    #this for grouping var attrs - like 1.quant, 2.state, etc
    def update_gv_attributes(self, entry, gv_num, row):
        if gv_num in self.gv_select_attrs:
            for attr in self.gv_select_attrs[gv_num]:
                if attr in row:
                    storage_key = f"gv_{gv_num}_{attr}"
                    # Store the first value we encounter for this GV attribute
                    if entry[storage_key] is None:
                        entry[storage_key] = row[attr]


"""

    #acc algorithm body
    body = """
    mf_struct = MFStruct(S, V, F, o, G)
    for sales_row in all_rows:
        mf_struct.populate_entries(sales_row)

    # to make our lives easier: will detect if query is emf off the bat
    # is_emf = False #lets assume we r in mf always for now. Edit eventually

    #also need to do 1 loop j for regular aggs
    for sales_row in all_rows:
        group_vals = {attr: sales_row[attr] for attr in mf_struct.grouping_attrs}
        matching_entry = None
        for entry in mf_struct.entries:
            if all(entry[attr] == group_vals[attr] for attr in mf_struct.grouping_attrs):
                matching_entry = entry
                break
        
        if matching_entry:
            #update overall aggs using gv number 0 lol
            mf_struct.update_aggregates(matching_entry, "0", sales_row)

    for grouping_var in range(1, n+1):
        conditions_list = o[grouping_var-1]
        for sales_row in all_rows:
            #get attributes of that row to find the entry needed if emf applies
            group_vals = {attr: sales_row[attr] for attr in mf_struct.grouping_attrs}
            matching_entry = None
            #print(mf_struct.entries)
            for entry in mf_struct.entries:
                if all(entry[attr] == group_vals[attr] for attr in mf_struct.grouping_attrs):
                    matching_entry = entry
                    break
            all_conditions_met = True
            
            for condition in conditions_list:
                #add matching entry so emf can access necessary depedent aggregates
                if not check_condition(sales_row, condition, str(grouping_var), matching_entry):
                    all_conditions_met = False
                    break
            if all_conditions_met: #then sales_row is valid
                mf_struct.update_aggregates(matching_entry, str(grouping_var), sales_row)

    for entry in mf_struct.entries:
        if evaluate_having(entry, G):
            select_vals = get_select_values(entry, S)
            final_results.append(select_vals)
    """

    # Note: The f allows formatting with variables.
    #       Also, note the indentation is preserved.
    tmp = f"""
import os
import psycopg2
import psycopg2.extras
import tabulate
import re
from dotenv import load_dotenv

# DO NOT EDIT THIS FILE, IT IS GENERATED BY generator.py
{definitions}
def query():
    load_dotenv()

    user = os.getenv('USER')
    password = os.getenv('PASSWORD')
    dbname = os.getenv('DBNAME')

    conn = psycopg2.connect(dbname=dbname, user=user, password=password,
                            cursor_factory=psycopg2.extras.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales")
    all_rows = cur.fetchall()
    S, n, V, F, o, G = {S, n, V, F, o, G}
    final_results = []
    {body}
    
    return tabulate.tabulate(final_results,
                        headers="keys", tablefmt="psql")

def main():
    print(query())
    
if "__main__" == __name__:
    main()
    """

    # Write the generated code to a file
    open("_generated.py", "w").write(tmp)
    # Execute the generated code
    subprocess.run(["python", "_generated.py"])


if "__main__" == __name__:
    main()
