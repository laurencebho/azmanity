import xlrd
import csv

def xlsx_to_csv(filename):
    wb = xlrd.open_workbook(filename)
    sh = wb.sheet_by_name('WRDS')
    with open('raw.csv', 'w') as fw:
        writer = csv.writer(fw, quoting=csv.QUOTE_ALL)
        for row in range(sh.nrows):
            writer.writerow(sh.row_values(row))

if __name__=='__main__':
    xlsx_to_csv('raw.xlsx')
