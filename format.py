#This contains what i THINK should be generated given some S, n, ..., G

S, n, V, F, o, G = 0, 0, 0, 0, 0, 0
class MFStruct:
    def __init__(self, grouping_attrs, aggregate_funcs): #essentially V and F
        self.entries = [] #i think its easiest if we make an array of dicts
        self.grouping_attrs = grouping_attrs
        self.aggregate_funcs = aggregate_funcs
        self.all_aggregate_names = self._get_all_agg_names()

    #gets all unique agg names 
    def _get_all_agg_names(self):
        names = set()
        for agg_func in self.aggregate_funcs:
            #agg_func = 1_sum_quant, 2_avg_sales, etc
            names.add(agg_func)
            #if it contains avg then we gotta add 2 more names
            if agg_func.startswith(('avg_', '_avg')) or 'avg' in agg_func.split('_')[1]:
                names.add(f"{agg_func}_count")
                names.add(f"{agg_func}_sum")
        return list(names)

    #finds tuple in mf_entries
    def find_entry(self, row):
        for entry in self.entries:
            match = all(entry[attr] == row[attr] for attr in self.grouping_attrs)
            if match:
                return entry
        return None
    
    #creates tuple in mf_entries
    def create_entry(self, row):
        new_entry = {}
        for attr in self.grouping_attrs:
            new_entry[attr] = row[attr]
        
        #init all agg columns to defaults
        for agg_name in self.all_aggregate_names:
            if agg_name.endswith('_count') or 'count' in agg_name.split('_')[1]:
                new_entry[agg_name] = 0
            elif agg_name.endswith('_sum') or 'sum' in agg_name.split('_')[1]:
                new_entry[agg_name] = 0
            elif agg_name.startswith(('max_', '_max')) or 'max' in agg_name.split('_')[1]:
                new_entry[agg_name] = -float('inf')
            elif agg_name.startswith(('min_', '_min')) or 'min' in agg_name.split('_')[1]:
                new_entry[agg_name] = float('inf')
            elif 'avg' in agg_name and not ('count' in agg_name or 'sum' in agg_name):
                new_entry[agg_name] = 0.0
            else:
                new_entry[agg_name] = 0 #default for count and sum for avg
        self.entries.append(new_entry)
        return new_entry

    #updates agg value in mf_entries
    def update_aggregate(self, entry, scan_num, row, agg_func_name):
        #again looks like 1_sum_quant, etc
        parts = agg_func_name.split('_')
        agg_type = parts[1] #sum, avg, etc
        attr_name = '_'.join(parts[2:]) #attr getting that func

        value = row[attr_name]

        if agg_type == "sum":
            entry[agg_func_name] += value
        elif agg_type == "count":
            entry[agg_func_name] += 1
        elif agg_type == "max":
            if entry[agg_func_name] is None or value > entry[agg_func_name]:
                entry[agg_func_name] = value
        elif agg_type == "min":
            if entry[agg_func_name] is None or value < entry[agg_func_name]:
                entry[agg_func_name] = value
        elif agg_type == "avg":
            count_name = f"{agg_func_name}_count"
            sum_name = f"{agg_func_name}_sum"
            entry[count_name] += 1
            entry[sum_name] += value
            entry[agg_func_name] = entry[sum_name] / entry[count_name] if entry[count_name] > 0 else 0

