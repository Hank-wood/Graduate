from client import client

def test_fetch_sorted_answers():
    question = client.question('https://www.zhihu.com/question/27459050?sort=created')
    count = 0
    for answer in question.answers:
        count += 1
        print(answer.author.name, answer.upvote_num, answer.author.motto)
    assert count >= 84


def test_collapsed_answers():
    url = 'https://www.zhihu.com/question/20936479'
    question = client.question(url)
    answers = list(question.answers)
    print(answers[-1].author.name)

    url = 'https://www.zhihu.com/question/20936479?sort=created'
    question = client.question(url)
    answers = list(question.answers)
    print(len(answers))



test_collapsed_answers()