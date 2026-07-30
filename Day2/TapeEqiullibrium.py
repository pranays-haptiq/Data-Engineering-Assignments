def solution(A):
    total_sum = sum(A)

    left_sum = 0
    min_difference = float("inf")

    for P in range(1, len(A)):
        left_sum += A[P - 1]

        right_sum = total_sum - left_sum

        current_difference = abs(left_sum - right_sum)

        if current_difference < min_difference:
            min_difference = current_difference

    return min_difference


A = [3, 1, 2, 4, 3]

result = solution(A)
print(result)
