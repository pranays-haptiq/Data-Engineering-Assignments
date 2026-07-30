def solution(A):
    A.sort()

    product1 = A[-1] * A[-2] * A[-3]

    product2 = A[0] * A[1] * A[-1]

    return max(product1, product2)


A = [-3, 1, 2, -2, 5, 6]

result = solution(A)
print(result)