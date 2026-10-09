# import pandas as pd

# pd.options.display.max_rows = 9999

# df = pd.read_csv('data.csv')

# print(df) 
import pandas as pd

a = [1, 7, 2]

myvar = pd.Series(a, index = ["x", "y", "z"])

print(myvar)