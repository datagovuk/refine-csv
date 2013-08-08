import unicodecsv
import re
import operator


# Keys IDs within the row
# -----
NAME = 0
PUBLISHER = 1
TITLE = 2
DESCRIPTION = 3
TAGS = 4
THEME_PRIMARY = 5

regex = re.compile(r'[^a-zA-Z0-9]+')

def load(csv_filename,with_keys=False):
    with open(csv_filename) as f:
        reader = unicodecsv.reader(f)
        data = list(reader)
        if not with_keys:
            data = data[1:]
        return data

def master_table(data,field_id):
    # Build a frequency table of words
    # { word : { 'Defence':49, 'Transport':12 ...} }
    # Tracking number of unique datasets it appears in
    master = {}
    theme_count = {}
    for row in data:
        theme = row[THEME_PRIMARY]
        textfield = row[field_id]
        for word in set( words_in(textfield) ):
            master[word] = master.get(word,{})
            master[word][theme] = master[word].get(theme,0) + 1
        # count the number of datasets in each theme
        theme_count[theme] = theme_count.get(theme,0) + 1
    # Normalise the table (themes vary in population)
    for word,freqs in master.items():
        for theme,count in freqs.items():
            if count==1:
                del freqs[theme]
        for theme in freqs.keys():
            freqs[theme] = float(freqs[theme]) / theme_count[theme]
        if u'' in freqs: 
            del freqs[u'']
        if not len(freqs):
            del master[word]
    return master

def debug(master):
    counts = {}
    for word,freqs in master.iteritems():
        count = len(freqs)
        counts[count] = counts.get(count,[])
        counts[count].append(word)
    return counts

def confidence_table(master):
    # Build a confidence table from the master table
    # word -> (theme, confidence)
    confidence_table = {}
    for word,freqs in master.iteritems():
        sort = sorted( freqs.items(), key=operator.itemgetter(1), reverse=True )
        theme = sort[0][0]
        confidence = sort[0][1]
        # Decrement confidence if the word appears in other themes
        for item in sort[1:]:
            confidence -= item[1]
        # Final confidence represents how much MORE OFTEN a word 
        # appears in the TOP THEME than in ALL OTHER THEMES COMBINED.
        if confidence>0:
            confidence_table[word] = (theme,confidence)
    return confidence_table

def words_in(string):
    string = regex.sub(' ',string)
    string = string.lower()
    words = string.split()
    return words

def calculate_guess(text_field,confidence_table):
    guesses = {}
    for word in words_in(text_field):
        if word not in confidence_table:
            continue
        theme,confidence = confidence_table[word]
        guesses[theme] = guesses.get(theme,0.0) + confidence
    return guesses

def one_guess(guesses):
    if not len(guesses):
        return '',0.0
    sort = sorted( guesses.iteritems(), key=operator.itemgetter(1), reverse=True )
    theme,confidence = sort[0]
    for theme2,confidence2 in sort[1:]:
        confidence -= confidence2
    if confidence<0:
        return '',0.0
    return theme,confidence

def guess_for_row(row,confidence_table):
    guesses = calculate_guess(row[DESCRIPTION],confidence_table)
    theme,confidence = one_guess(guesses)
    return theme,confidence

def augment_csv(src_csv,dest_csv):
    data = load(src_csv,with_keys=True)
    master_description = master_table(data[1:],DESCRIPTION)
    con_description = confidence_table(master_description)
    master_tags = master_table(data[1:],TAGS)
    con_tags = confidence_table(master_tags)
    master_title = master_table(data[1:],TITLE)
    con_title = confidence_table(master_title)
    data[0].append('guess_description')
    data[0].append('confidence')
    data[0].append('guess_tags')
    data[0].append('confidence')
    data[0].append('guess_title')
    data[0].append('confidence')
    for n in range(1,len(data)):
        theme,confidence = guess_for_row(data[n],con_description)
        data[n].append(theme)
        data[n].append(confidence)
        theme,confidence = guess_for_row(data[n],con_tags)
        data[n].append(theme)
        data[n].append(confidence)
        theme,confidence = guess_for_row(data[n],con_title)
        data[n].append(theme)
        data[n].append(confidence)
    with open(dest_csv,'w') as f:
        unicodecsv.writer(f).writerows(data)

