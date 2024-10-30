# Source: https://github.com/devdatalab/masala-merge
# Modified to include some extra pairings

import string

# specify single-letter pairs that have a low cost match.
# specify each one twice, i.e. both directions so can be a fast lookup
pair_1to1 = set(['YE', 'EY', 'UW', 'WU', 'DT', 'TD', 'AE', 'AI', 'AO', 'AU', 'EA', 'EI', 'EO', 'EU', 'IA', 'IE', 'IO', 'IU', 'OA', 'OE', 'OI', 'OU', 'UA', 'UE', 'UI', 'UO', 'SZ', 'ZS', 'BV', 'VB', 'OW', 'WO', 'YI', 'IY', 'RD', 'DR', 'CK', 'KC', 'CS', 'SC', 'GJ', 'JG', 'ZJ', 'JZ', 'XZ', 'ZX', 'XS', 'SX', 'XJ', 'JS', 'SZ', 'ZS', 'KQ', 'QK', 'WV', 'VW', 'BV', 'VB', 'PF', 'FP', 'KG', 'GK'])

# 2to2 lists mean cheap processing of character transposition
pair_2to2 = set(['EV', 'EO', 'CK', 'KC', 'KQ', 'QK', 'PF', 'FP', 'GJ', 'JG', 'BV', 'VB', 'VW', 'WV', 'BW', 'WB', 'JZ', 'ZJ', 'XZ', 'ZX', 'XS', 'SX', 'ZS', 'SZ', 'SC', 'CS', 'YU', 'UY', 'AU', 'UA', 'EU', 'UE', 'IU', 'UI', 'IO', 'OI'])

# 2to1
pair_2to1_list = ['O-OW', 'U-UW', 'U-OO', 'E-IY', 'I-IY', 'X-KS', 'E-EE' , 'O-OO', 'S-SC' , 'X-XC', 'X-KS', 'I-EE', 'A-YA', 'L-ZH']

# dictionary for cheap single letter omissions. spaces are free, but non-zero to avoid duplication problems.
pair_1to0 = {'A':0.2, 'E': 0.2, 'H':0.2, 'U':0.3, 'N':0.45, ' ': 0.01, '(': 0.01, ')': 0.01, '[': 0.01, ']': 0.01, '.': 0.01, '-': 0.01, '*': 0.01 }

cost_swap = 0.45
cost_1to1 = 0.45
cost_2to2 = 0.2
cost_2to1 = 0.2
cost_double_letter = 0.1

# specify additional penalty for mismatched digits. (so village1 doesn't match village2)
digit_cost = 1.5

# other potential rules
# - N + consonant -> consonant
# - first letter wrong = cost 1.5

# N+consonant -> consonant: .25
# nb nc nd nf ng nh -> 0.8?

# INSERT / DELETE COSTS
# W/Y -> 0.5


# initialize 2 to 1 matching dictionary
# format is [single-letter] -> [first of double-letter] -> [list of second of double-letter]
pair_2to1 = {}

# convert 2-to-1 list into a dictionary:
for item in pair_2to1_list:

    if item[0] not in pair_2to1:
        pair_2to1[item[0]] = {}

    if item[2] not in pair_2to1[item[0]]:
        pair_2to1[item[0]][item[2]] = []

    if item[3] not in pair_2to1[item[0]][item[2]]:
        pair_2to1[item[0]][item[2]].append(item[3])



# possible modifications
# 1:1 substitutions:

#  x replacement is diagonal. so each time, could test for a close
#    letter and pay a smaller diagonal cost

#  x replacing 1 letter for two, use a knight's move.

#  x 2-for-2?  same strategy should work

#  x add character swap as single operation

# x save time by quitting if minimum distance in a row is > X.

# KENISTON'S RULES

  # TRANSPOSITION COSTS
  # swap two vowels in valid vowel pair list [au, eu, iu, io] : cost is 0.15
  # swap vowel with consonant: cost is 0.25
  # swap vowel with R: 0.15
  # swap two consonants: 0.35
  
  # INSERT / DELETE COSTS
  # W/Y -> 0.5
  
  # SUBSTITUTION COSTS
  # base cost: 1
  # vowels in valid list: 0.25
  # # -> ! and vice versa? : 0.05
  # "YI" "IY" "RD" "DR" "CK" "KC" "CS" "SC" "GJ" "JG" "ZJ" "JZ" "XZ" "ZX" "XS" "SX" "XJ" "JS" "SZ" "ZS" "KQ" "QK" "WV" "VW" "BV" "VB" "PF" "FP" : 0.25
  # "KQ" "QK" "WV" "VW" "BV" "VB" "PF" "FP" : 0.15
  
  # another substituion or translation list:
  # "CK" "KC" "KQ" "QK" "PF" "FP" "GJ" "JG" "BV" "VB" "VW" "WV" "BW" "WB" "JZ" "ZJ" "XZ" "ZX" "XS" "SX" "ZS" "SZ" "SC" "CS" "YU" "UY"
  
  # char list + H
  # N + consonant = consonant
  
  # INSERT / DELETE COSTS
  # W/Y -> 0.5
#

MIN_DIST_FILTER = 100

def update_matrix(matrix, row, col, value):
    if row >= len(matrix) or col >= len(matrix[0]): return
    if matrix[row][col] > value: matrix[row][col] = value

# internet levensthein
def masala_levenshtein(str1, str2):
    s1 = str1 + " "
    s2 = str2 + " "

    l1 = len(s1)
    l2 = len(s2)

    # initialize matrix with worst case.
    matrix = [list(range(l1 + 1))] * (l2 + 1)
    for c2 in range(l2 + 1):
        matrix[c2] = list(range(c2,c2 + l1 + 1))
    
    # loop over each row
    for c2 in range(0,l2):

        # store minimum distance in this row
        min_dist = MIN_DIST_FILTER

        # loop over each column
        for c1 in range(0,l1):

            # update minimum distance if this is lower than current minimum
            if matrix[c2][c1] < min_dist: min_dist = matrix[c2][c1]

            # adjust right step, down step (characters dropped), and right-down step (character substitution)
            update_matrix(matrix, c2+1, c1, matrix[c2][c1] + 1)
            update_matrix(matrix, c2, c1+1, matrix[c2][c1] + 1)
            update_matrix(matrix, c2+1, c1+1, matrix[c2][c1] + 1)

            # if this position is a match
            if s1[c1] == s2[c2]:

                # set down-right cell to minimum of (right + 1, down + 1, this cell)
                update_matrix(matrix, c2+1, c1+1, matrix[c2][c1])

            # cheaper right step if c1 is in pair_1to0
            if s1[c1] in pair_1to0:
                update_matrix(matrix, c2, c1+1, matrix[c2][c1] + pair_1to0[s1[c1]])

            # cheaper down step if c2 is in pair_1to0
            if s2[c2] in pair_1to0:
                update_matrix(matrix, c2+1, c1, matrix[c2][c1] + pair_1to0[s2[c2]])

            # if the letters are close
            if (s1[c1] + s2[c2]) in pair_1to1:

                # pay 1to1 cost in right-down cell.
                update_matrix(matrix, c2+1, c1+1, matrix[c2][c1] + cost_1to1)

            # tricky part, if we find a match in the 2to1 list, adjust a knight's move number.
            # this is separate from the other if block, since it doesn't affect the diagonal square.
            if c1 < (l1-0) and c2 < (l2-1) and s1[c1] in pair_2to1 and s2[c2] in pair_2to1[s1[c1]] and s2[c2+1] in pair_2to1[s1[c1]][s2[c2]]:

                # jump to 1 step right, 2 steps down
                update_matrix(matrix, c2+2, c1+1, matrix[c2][c1] + cost_2to1)

            # now check for a matching pair_ going the other way
            if c2 < (l2-0) and c1 < (l1-1) and s2[c2] in pair_2to1 and s1[c1] in pair_2to1[s2[c2]] and s1[c1+1] in pair_2to1[s2[c2]][s1[c1]]:

                # jump to 1 step down, 2 steps right
                update_matrix(matrix, c2+1, c1+2, matrix[c2][c1] + cost_2to1)

            # check for character position swap, and adjust +2,+2 matrix location
            if c2 < (l2-1) and c1 < (l1-1) and ((s1[c1] + s1[c1 + 1]) == (s2[c2+1] + s2[c2])):

                # if in cheap list, do it cheaply
                if (s1[c1] + s1[c1 + 1]) in pair_2to2:
                    update_matrix(matrix, c2+2, c1+2, matrix[c2][c1] + cost_2to2)

                else:
                    update_matrix(matrix, c2+2, c1+2, matrix[c2][c1] + cost_swap)

            # if single letter matches a double letter, low cost knight's move (1 right 2 down)
            if c1 < (l1-0) and c2 < (l2-1) and s1[c1] == s2[c2] and s1[c1] == s2[c2+1]:
                update_matrix(matrix, c2+2, c1+1, matrix[c2][c1] + cost_double_letter)

            # ditto, 1 down 2 right
            if c1 < (l1-1) and c2 < (l2-0) and s1[c1] == s2[c2] and s1[c1+1] == s2[c2]:
                update_matrix(matrix, c2+1, c1+2, matrix[c2][c1] + cost_double_letter)

        # if the lowest distance is too large, exit
        if min_dist >= MIN_DIST_FILTER: return MIN_DIST_FILTER

    return matrix[l2][l1]

def get_digits(s):
    digits = ""
    for c in s:
        # if this is a digit (ascii value between 48 and 57)
        if ord(c) >= 48 and ord(c) <= 57:
            digits += c
    return digits


#calculates additional cost of comparison between two string.
#returns additional cost
def digit_compare(string1, string2):

    first_digits = get_digits(string1)
    second_digits = get_digits(string1)

    # run levenshtein again on just the digit strings
    digit_penalty = digit_cost * levenshtein(first_digits, second_digits)

    # return digit penalty
    return digit_penalty
