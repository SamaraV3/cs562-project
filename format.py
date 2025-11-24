#This contains what i THINK should be generated given some S, n, ..., G

S, n, V, F, o, G = ["0"], 0, ["0"], [["0"], ["0"]], [["0"], ["0"]], 0
cur = [] #acc contains sales data. will del when acc adding to gen.py

def check_condition(row, condition, grouping_var):
    #check if row satisfies a condition for a grouping var
    if not condition or condition == "0": #no condition exists for this - assume we good
        return True
    #condits in form 1.state=, 2.quant>, etc
    #remove grouping_var_prefix
    condition_without_gv = condition.replace(f"{grouping_var}.", "", 1)
    operators = ['=', '!=', '>', '>=', '<', '<=']
    for op in operators:
        if op in condition_without_gv:
            left, right = condition_without_gv.split(op, 1) #left of op vs right of op
            left = left.strip()
            right = right.strip().strip("")

            if left not in row:
                return False #attribute doesnt event exist IN the row
            row_value = row[left]

            if op == '=':
                return str(row_value) == right
            elif op == '!=':
                return str(row_value) != right
            elif op == '>':
                return float(row_value) > float(right)
            elif op == '>=':
                return float(row_value) >= float(right)
            elif op == '<':
                return float(row_value) < float(right)
            elif op == '<=':
                return float(row_value) <= float(right)

    return False #the input condition has eluded my capabilities

def evaluate_having(entry, having_condition):
    if not having_condition or having_condition == "0":
        return True
    
    # Replace aggregate references with actual values from entry
    # Example: "1_sum_quant > 2 * 2_sum_quant" becomes "entry['1_sum_quant'] > 2 * entry['2_sum_quant']"
    condition_to_eval = having_condition
    
    # Simple replacement
    for agg_func in mf_struct.all_agg_funcs:
        if agg_func in having_condition:
            condition_to_eval = condition_to_eval.replace(agg_func, f"entry['{agg_func}']")
    
    # Also handle non-aggregate references if any
    for attr in mf_struct.grouping_attrs:
        if attr in having_condition:
            condition_to_eval = condition_to_eval.replace(attr, f"entry['{attr}']")
    
    try:
        return eval(condition_to_eval)
    except:
        return False

def get_select_values(entry, select_attrs):
    result = []
    for attr in select_attrs:
        if attr in entry:
            # This is a grouping attribute or aggregate function
            result.append(entry[attr])
        elif any(attr.startswith(f"{i}_") for i in range(1, n+1)):
            # This is a non-aggregate grouping variable attribute like "1_date"
            # For now, we don't have these in our mf-structure
            result.append(None)  # Placeholder
        else:
            result.append(None)  # Unknown attribute
    
    return result

class MFStruct:
    def __init__(self, proj_attrs, grouping_attrs, agg_func_set, pred_set):
        self.proj_attrs = proj_attrs #S
        self.grouping_attrs = grouping_attrs #V
        self.all_agg_funcs = [item for sublist in agg_func_set for item in sublist] #F - list of lists
        self.pred_set = [item for sublist in pred_set for item in sublist] #o - list of lists
        self.entries = [] 
        #mf entries are only for grouping attributes and aggregate functions
        #can worry abt when non aggs show in select LATER


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
        
        self.entries.append(new_entry)
        return new_entry
        
    def update_aggregates(self, entry, gv_num, row):
        for agg_func in self.all_agg_funcs:#iterate over all agg_funcs
            if agg_func.startswith(f"{gv_num}_"):
                parts = agg_func.split('_')
                agg_type = parts[1]
                attr_name = '_'.join(parts[2:])
                
                if attr_name not in row:
                    continue  # Skip if attribute doesn't exist in row
                
                value = row[attr_name]
                
                if agg_type == "sum":
                    entry[agg_func] += value
                elif agg_type == "count":
                    entry[agg_func] += 1
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




mf_struct = MFStruct(S, V, F, o)
for sales_row in cur:
    mf_struct.populate_entries(sales_row)

# to make our lives easier: will detect if query is emf off the bat
is_emf = False #lets assume we r in mf always for now. Edit eventually

for grouping_var in range(1, n+1):
    condition = o[grouping_var-1]
    for sales_row in cur:
        if check_condition(sales_row, condition, grouping_var): #then sales_row is valid
            if is_emf:#find row in emf where its a matching group - too hard for rn
                pass
            else:
                group_vals = {attr: sales_row[attr] for attr in mf_struct.grouping_attrs}
                matching_entry = None
                for entry in mf_struct.entries:
                    if all(entry[attr] == group_vals[attr] for attr in mf_struct.grouping_attrs):
                        matching_entry = entry
                        break
                if matching_entry:
                    mf_struct.update_aggregates(matching_entry, grouping_var, sales_row)

final_results = []
for entry in mf_struct.entries:
    if evaluate_having(entry, G):
        select_vals = get_select_values(entry, S)
        final_results.append(select_vals)

#Print final results
for res in final_results:
    print(dict(zip(S, res)))