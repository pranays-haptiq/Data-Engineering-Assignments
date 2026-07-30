def solution(A):

    N = len(A)

    n = N + 1
    expected_sum = n * (n + 1) // 2

    actual_sum = sum(A)

    return expected_sum - actual_sum


A = [2, 3, 1, 5]

result = solution(A)
print(result)