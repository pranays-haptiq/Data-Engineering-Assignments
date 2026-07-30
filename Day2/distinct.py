def solution(A):
    unique_values = set(A)
    return len(unique_values)


A = [2, 1, 1, 2, 3, 1]

result = solution(A)
print(result)