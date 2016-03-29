from iutils import longestIncreasingSubsequence


nums = [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]
lis, index_list = longestIncreasingSubsequence(nums)
print(lis)
print(index_list)

for index, num in zip(index_list, lis):
    assert nums[index] == num