'''
A Python script to arrange the .tex files into one file. 
The program will detect the \input{*} commands in the main .tex file, and merge them recursively.
Before using this script, please ensure the Latex project could be compiled successfully.
Usage:
    1. Move this script into the root directory of your Latex project. 
       Usually, the main .tex file will aslo be listed here.
    2. Run this script in the format of 
       python arrange.py {main}.tex {merged_main}.tex
    E.g. if you have a main .tex file named latex.tex, you can run 
       python arrange.py latex.tex merged_latex.tex
'''

def arrange_tex(filename):
    text = open(filename,'r')
    data = text.readlines()
    text.close()
    arranged_data = []
    for line in data:
        arranged_lines =[]
        comment_idx = line.find('%')
        while comment_idx >0:
            if line[comment_idx-1] != '\\':
                break
            comment_idx = line.find('%',comment_idx+1)   
        start_idx = line.find('\input',0,comment_idx)
        while start_idx!=-1:
            arranged_lines.append(line[0:start_idx])
            end_idx = line.find('}',start_idx,comment_idx)
            if end_idx == -1:
                print("Missing } inserted.",line)
            sub_filename = line[start_idx+7:end_idx] # the length of '\input{' is 7
            if not sub_filename.endswith('.tex'):
                sub_filename += '.tex'
            arranged_lines += arrange_tex(sub_filename)
            start_idx = line.find('\input',end_idx,comment_idx)
        if arranged_lines:
            arranged_data += arranged_lines
        else:
            arranged_data.append(line)
    arrange_data.append('\n')
    return arranged_data

if __name__  == '__main__':
    import sys
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    if not input_filename.endswith('.tex'):
        raise Exception('Input must be .tex.')
    if not output_filename.endswith('.tex'):
        raise Exception('Output must be .tex.')
    arrange_data =  arrange_tex(input_filename)
    with open(output_filename, "w") as f:
        f.writelines(arrange_data)
            

