import math


def print_neatly_optimizer(words, n, M):
    """
    Function prints a paragraph neatly
    @param words : an array of words
    @param n : number of words in the array
    @param M : maximum line length
    """
    minpenalty = [float('inf')]*(n+1)
    break_points = [None]*(n+1)

    # initialize base case
    minpenalty[0] = 0

    def compute_line_cost(extra_space, j, n):
        if extra_space < 0:
            return float('inf')
        elif j == n and extra_space >= 0:
            return 0
        else:
            return extra_space**3

    for j in range(1, n+1):
        extra_space = M + 1
        for i in range(j, int(max(1, j + 1 - math.ceil(M/2)))-1, -1):
            extra_space = extra_space - len(words[i]) - 1
            cur_penalty = minpenalty[i-1] + compute_line_cost(extra_space, j, n)
            if minpenalty[j] > cur_penalty:
                minpenalty[j] = cur_penalty
                break_points[j] = i

    return minpenalty, break_points


def reconstruct_lines(text, j, break_points):
    i = break_points[j]
    neat_text = []
    if i != 1:
        neat_text = reconstruct_lines(text, i-1, break_points)
    neat_text.append(' '.join(text[i:(j+1)]))
    return neat_text


def print_neatly(text, M):
    n = len(text.split(' '))
    text = ['BLANK'] + text.split(' ')
    min_p, p_list = print_neatly_optimizer(text, n, M)
    neat_text = reconstruct_lines(text, n, p_list)
    return neat_text


# adapted from: https://github.com/samuelklam/print-neatly/blob/master/print-neatly.py
if __name__ == '__main__':
    text = "Buffy the Vampire Slayer fans are sure to get their fix with the DVD release of the show's first season. The three-disc collection includes all 12 episodes as well as many extras. There is a collection of interviews by the show's creator Joss Whedon in which he explains his inspiration for the show as well as comments on the various cast members. Much of the same material is covered in more depth with Whedon's commentary track for the show's first two episodes that make up the Buffy the Vampire Slayer pilot. The most interesting points of Whedon's commentary come from his explanation of the learning curve he encountered shifting from blockbuster films like Toy Story to a much lower-budget television series. The first disc also includes a short interview with David Boreanaz who plays the role of Angel. Other features include the script for the pilot episodes, a trailer, a large photo gallery of publicity shots and in-depth biographies of Whedon and several of the show's stars, including Sarah Michelle Gellar, Alyson Hannigan and Nicholas Brendon."
    M = 40
    neat_text = print_neatly(text, M)
    print(neat_text)
