## frogjump

def solution(X, Y, D):
    distance = Y - X

    if distance % D == 0:
        return distance // D
    else:
        return (distance // D) + 1


X = 10
Y = 85
D = 30

result = solution(X, Y, D)
print(result)